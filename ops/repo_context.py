#!/usr/bin/env python3
"""Pull live facts from a registered repo before making any claim about it.

  python3 ops/repo_context.py --repo shop-api --terms "refund order"

Reports the repo's current branch, latest commit, uncommitted changes, its
rules file and status file, and where the search terms appear, split into
running code, tests, and docs. Matches in code are leads to read, not proof.
Matches only in docs or plans mean the feature may be planned, not built.

Read-only: it runs only read commands (git rev-parse, git status) and reads
files. It never edits, builds, tests, or commits in the target repo.

Exit codes: 0 = the minimum live context is complete (rules file, status file,
and a readable commit); 1 = something in that minimum is missing; 2 = could
not run (unknown repo, missing folder, not a git repo).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hqlib  # noqa: E402

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "coverage",
    "vendor", "site-packages", ".pytest_cache", ".mypy_cache", ".tox", "tmp", "output",
}
TEXT_SUFFIXES = {
    "", ".c", ".cc", ".cfg", ".cpp", ".cs", ".css", ".go", ".graphql", ".h", ".html", ".ini",
    ".java", ".js", ".json", ".jsx", ".kt", ".md", ".mjs", ".php", ".proto", ".py", ".rb",
    ".rs", ".rst", ".scss", ".sh", ".sql", ".swift", ".toml", ".ts", ".tsx", ".txt",
    ".vue", ".xml", ".yaml", ".yml",
}
SECRET_MARKERS = (".env", "credential", "secret", "private_key", "id_rsa", ".pem", ".key")
STATUS_CANDIDATES = ("STATUS.md", "docs/STATUS.md")
MAX_FILE_BYTES = 512_000
MAX_FILES = 10_000
MAX_MATCHES = 12
CATEGORIES = ("code", "tests", "docs")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=hqlib.git_env(), check=False)
    if result.returncode != 0:
        raise hqlib.HQError(f"{repo} is not a readable git repository ({result.stderr.strip() or 'git failed'})")
    return result.stdout.strip()


def identity(repo: Path) -> Tuple[str, str, int, int]:
    top = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if top != repo.resolve():
        raise hqlib.HQError(f"{repo} is inside the git repository at {top}, not a repository of its own")
    try:
        head = git(repo, "rev-parse", "HEAD")
    except hqlib.HQError:
        head = ""
    try:
        branch = git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    except hqlib.HQError:
        branch = "(detached)"
    lines = [line for line in git(repo, "status", "--porcelain").splitlines() if line]
    untracked = sum(1 for line in lines if line.startswith("??"))
    return branch, head, len(lines) - untracked, untracked


def is_secret(rel: Path) -> bool:
    lowered = rel.as_posix().lower()
    return any(marker in lowered for marker in SECRET_MARKERS)


def category(rel: Path) -> str:
    parts = [p.lower() for p in rel.parts]
    name = rel.name.lower()
    if rel.suffix.lower() in {".md", ".rst", ".txt"} or "docs" in parts:
        return "docs"
    if {"tests", "test", "__tests__", "spec"} & set(parts) or name.startswith("test_") or ".test." in name or ".spec." in name or name.endswith("_test.py") or name.endswith("_test.go"):
        return "tests"
    return "code"


def files(repo: Path) -> Iterable[Path]:
    for current, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(names):
            path = Path(current) / name
            rel = path.relative_to(repo)
            if name.startswith(".") or is_secret(rel) or path.is_symlink():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            yield path


def words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search(repo: Path, terms: str) -> Tuple[Dict[str, List[str]], int, bool, Dict[str, int]]:
    wanted = words(terms)
    if not wanted:
        raise hqlib.HQError("--terms needs at least one word to search for")
    found: Dict[str, List[str]] = {c: [] for c in CATEGORIES}
    scanned = 0
    truncated = False
    file_counts: Dict[str, int] = {c: 0 for c in CATEGORIES}
    for path in files(repo):
        if scanned >= MAX_FILES:
            truncated = True
            break
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        rel = path.relative_to(repo)
        file_counts[category(rel)] += 1
        bucket = found[category(rel)]
        if len(bucket) >= MAX_MATCHES:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            line_words = set(words(line))
            if all(w in line_words for w in wanted):
                excerpt = " ".join(line.split())
                excerpt = re.sub(r"(?i)((?:api[_-]?key|password|secret|token)\s*[:=]\s*)\S+", r"\1<hidden>", excerpt)
                bucket.append(f"{rel.as_posix()}:{number}  {excerpt[:200]}")
                if len(bucket) >= MAX_MATCHES:
                    break
    return found, scanned, truncated, file_counts


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="repo name as registered in hq.yaml")
    parser.add_argument("--terms", required=True, help="words that describe the capability, searched together")
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    args = parser.parse_args(argv)
    try:
        root = hqlib.find_root(args.root)
        repo = hqlib.find_repo(root, args.repo)
        if not repo.path.is_dir():
            raise hqlib.HQError(f"'{repo.name}' is registered at {repo.path}, but that folder does not exist")
        branch, head, changed, untracked = identity(repo.path)
        found, scanned, truncated, file_counts = search(repo.path, args.terms)
    except hqlib.HQError as exc:
        print(f"Repo context could not run: {exc}")
        return 2

    rules_name = repo.rules_file or "AGENTS.md"
    rules = repo.path / rules_name
    status_names = [repo.entry["status_file"]] if hqlib.is_text(repo.entry.get("status_file")) else list(STATUS_CANDIDATES)
    status = next((repo.path / n for n in status_names if (repo.path / n).is_file()), None)

    print(f"Live context for {repo.name}")
    print(f"Folder: {repo.path}")
    print(f"Branch: {branch}")
    print(f"Latest commit: {head or '(no commits yet)'}")
    print(f"Uncommitted: {changed} changed file(s), {untracked} new file(s)")
    deploys = repo.deploys_from_main
    if not isinstance(deploys, bool):
        print("Release rule: not recorded in hq.yaml. Ask before pushing main.")
    elif deploys:
        print("Release rule: pushing main deploys to production. Treat a push to main as a release.")
    else:
        print("Release rule: main does not deploy automatically.")
    print(f"Rules file: {rules_name if rules.is_file() else 'MISSING (' + rules_name + ')'}")
    print(f"Status file: {status.relative_to(repo.path).as_posix() if status else 'MISSING'}")
    print("")
    print(f'Where "{args.terms}" appears ({scanned} files searched):')
    labels = {
        "code": "Code (leads to read, not proof)",
        "tests": "Tests",
        "docs": "Docs and plans (pointers only)",
    }
    for key in CATEGORIES:
        print(f"  {labels[key]}:")
        if not found[key]:
            print("    none")
        for hit in found[key]:
            print(f"    {hit}")
    print("")
    software_files = file_counts["code"] + file_counts["tests"]
    mostly_docs = file_counts["code"] == 0 or file_counts["docs"] >= 4 * software_files
    if found["code"]:
        print("Reading: code mentions these terms. Open those files and their callers before saying the feature works.")
    elif found["tests"]:
        print("No code mentions these terms; only tests do.")
        print("Reading: a test alone does not show a working feature. Find the code it exercises before making a claim.")
    else:
        print("No code or tests mention these terms.")
        if found["docs"] and mostly_docs:
            print(
                "Reading: this repository is mostly documents, so the docs matches may be the content itself. "
                "For any claim about software behavior, they are pointers only."
            )
        elif found["docs"]:
            print("Reading: only docs or plans mention them. That shows intent, not a working feature.")
        else:
            print("Reading: no matches at all. Do not conclude the feature is absent; try other words or read the entry points.")
    complete = rules.is_file() and status is not None and bool(head) and not truncated
    if truncated:
        print(f"Search stopped after {MAX_FILES} files, so results are partial.")
    if complete:
        print("Minimum live context: complete (the rules file, status file and latest commit were readable).")
    else:
        print("Minimum live context: incomplete")
    if not complete:
        missing = []
        if not rules.is_file():
            missing.append("a rules file")
        if status is None:
            missing.append("a status file")
        if not head:
            missing.append("a commit")
        if missing:
            print(f"Missing: {', '.join(missing)}. Say so in any answer about this repo.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
