#!/usr/bin/env python3
"""Catch stale, orphaned, or broken headquarters documents.

Checks every Markdown file under docs/ (except docs/archive/):

* Stale: each doc starts with a review line such as
      <!-- reviewed: 2026-11-12 | review every: 7 days -->
  (or "review every: as needed"). A doc past its review window fails.
* Orphaned: each doc must be reachable by links or path mentions starting from
  README.md, AGENTS.md, CLAUDE.md or SETUP.md. A doc nobody can find is either
  missing a link or should move to docs/archive/.
* Broken links: a relative Markdown link that points at a missing file fails.
* History in the startup path: AGENTS.md and CLAUDE.md must not send agents
  into docs/archive/, because archived material is history, not instructions.

Read-only. Exit codes: 0 = no problems, 1 = problems found, 2 = could not run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hqlib  # noqa: E402

ENTRY_POINTS = ("README.md", "AGENTS.md", "CLAUDE.md", "SETUP.md")
STARTUP_FILES = ("AGENTS.md", "CLAUDE.md")
ARCHIVE = "docs/archive/"
REVIEW_RE = re.compile(
    r"<!--\s*reviewed:\s*(?P<date>\S+)\s*\|\s*review every:\s*(?P<every>[^>]*?)\s*-->"
)
EVERY_RE = re.compile(r"^(?P<days>[1-9][0-9]*) days?$")
MD_REF_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.md\b")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def doc_files(root: Path) -> List[Path]:
    docs = root / "docs"
    if not docs.is_dir():
        return []
    return sorted(
        p for p in docs.rglob("*.md") if not _rel(root, p).startswith(ARCHIVE)
    )


def reachable(root: Path) -> Set[str]:
    """Files reachable from the entry points through .md mentions."""
    found: Set[str] = set()
    queue = [root / name for name in ENTRY_POINTS if (root / name).is_file()]
    seen = {p.resolve() for p in queue}
    while queue:
        current = queue.pop()
        found.add(_rel(root, current))
        for ref in MD_REF_RE.findall(_read(current)):
            for candidate in (root / ref, current.parent / ref):
                candidate = candidate.resolve()
                try:
                    candidate.relative_to(root)
                except ValueError:
                    continue
                if candidate.is_file() and candidate not in seen:
                    seen.add(candidate)
                    queue.append(candidate)
                    break
    return found


def check_docs(root: Path, today: Optional[dt.date] = None) -> List[str]:
    root = root.resolve()
    today = today or dt.date.today()
    problems: List[str] = []
    docs = doc_files(root)
    linked = reachable(root)

    for path in docs:
        rel = _rel(root, path)
        head = "\n".join(_read(path).splitlines()[:5])
        match = REVIEW_RE.search(head)
        if not match:
            problems.append(
                f"{rel}: missing its review line. Put "
                "'<!-- reviewed: YYYY-MM-DD | review every: 30 days -->' (or 'as needed') at the top."
            )
        else:
            reviewed = hqlib.as_date(match.group("date"))
            every = match.group("every").strip()
            days_match = EVERY_RE.match(every)
            if reviewed is None:
                problems.append(f"{rel}: review date '{match.group('date')}' must be written as YYYY-MM-DD.")
            elif reviewed > today:
                problems.append(f"{rel}: review date {reviewed.isoformat()} is in the future.")
            elif every != "as needed" and not days_match:
                problems.append(f"{rel}: 'review every' must be a number of days (like '7 days') or 'as needed'.")
            elif days_match:
                age = (today - reviewed).days
                limit = int(days_match.group("days"))
                if age > limit:
                    problems.append(
                        f"{rel}: stale. Last reviewed {reviewed.isoformat()} ({age} days ago); it should be "
                        f"checked every {limit} days. Re-read it against the live repos, fix it, and update the date."
                    )
        if rel not in linked:
            problems.append(
                f"{rel}: orphaned. Nothing reachable from README.md, AGENTS.md, CLAUDE.md or SETUP.md "
                "mentions it. Link it from the task router in AGENTS.md, or move it to docs/archive/."
            )

    checked = [root / name for name in ENTRY_POINTS if (root / name).is_file()] + docs
    for path in checked:
        rel = _rel(root, path)
        for target in LINK_RE.findall(_read(path)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            if not (path.parent / target_path).exists():
                problems.append(f"{rel}: link to '{target}' points at a file that does not exist.")

    for name in STARTUP_FILES:
        path = root / name
        if not path.is_file():
            continue
        for ref in MD_REF_RE.findall(_read(path)) + LINK_RE.findall(_read(path)):
            if ARCHIVE in ref or ref.startswith("archive/"):
                problems.append(
                    f"{name}: sends agents into archived history ('{ref}'). Startup instructions "
                    "should point only at current documents."
                )
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    parser.add_argument("--today", help="pretend today is this date (YYYY-MM-DD); useful in tests")
    args = parser.parse_args(argv)
    try:
        today = hqlib.parse_today(args.today)
        root = hqlib.find_root(args.root)
    except hqlib.HQError as exc:
        print(f"Docs check could not run: {exc}")
        return 2
    problems = check_docs(root, today)
    print(f"Docs checked: {len(doc_files(root))} (in {root / 'docs'}, not counting docs/archive/)")
    if problems:
        print(f"Problems: {len(problems)}")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Problems: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
