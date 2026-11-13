#!/usr/bin/env python3
"""Check the registry (hq.yaml): every repo is real, described, and has a release rule.

Read-only. It never writes to hq.yaml or to any registered repo.

Exit codes: 0 = no problems, 1 = problems found, 2 = the check could not run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hqlib  # noqa: E402

HQ_KEYS = {"name", "repos_root"}
REPO_KEYS = {
    "path",
    "purpose",
    "rules_file",
    "status_file",
    "main_deploys_to_production",
    "release_notes",
    "groups",
    "uses",
}
REQUIRED_REPO_KEYS = ("purpose", "main_deploys_to_production")
TOP_KEYS = {"hq", "repos", "groups"}


def check_registry(root: Path, data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[str]]:
    """Return (problems, notes). Problems fail the check; notes do not."""
    problems: List[str] = []
    notes: List[str] = []
    if data is None:
        data = hqlib.load_registry_data(root)

    for key in data:
        if key not in TOP_KEYS:
            problems.append(
                f"hq.yaml has an unknown top-level section '{key}'. Allowed: {', '.join(sorted(TOP_KEYS))}."
            )

    hq = data.get("hq")
    if not isinstance(hq, dict):
        problems.append("hq.yaml needs an 'hq:' section with at least 'repos_root'.")
        hq = {}
    for key in hq:
        if key not in HQ_KEYS:
            problems.append(f"hq: unknown setting '{key}'. Allowed: {', '.join(sorted(HQ_KEYS))}.")
    if not hqlib.is_text(hq.get("repos_root")):
        problems.append("hq: 'repos_root' must say which folder holds your repos (for example '..').")
    else:
        base = hqlib.repos_root(root, data)
        if not base.is_dir():
            problems.append(f"hq: repos_root points at a folder that does not exist: {base}")

    raw_repos = data.get("repos")
    if raw_repos is not None and not isinstance(raw_repos, dict):
        problems.append("'repos' must list each repo by name, like 'my-app:' followed by its settings.")
        return problems, notes
    raw_repos = raw_repos or {}
    if not raw_repos:
        notes.append("No repos are registered yet. Ask your agent to 'Set up my headquarters'.")

    seen_paths: Dict[Path, str] = {}
    for repo in hqlib.registered_repos(root, data):
        entry = raw_repos.get(repo.name)
        label = f"repo '{repo.name}'"
        if not isinstance(entry, dict):
            problems.append(f"{label}: needs settings underneath it (purpose, main_deploys_to_production, ...).")
            continue
        for key in entry:
            if key not in REPO_KEYS:
                problems.append(
                    f"{label}: unknown setting '{key}'. Allowed: {', '.join(sorted(REPO_KEYS))}."
                )
        for key in REQUIRED_REPO_KEYS:
            if key not in entry:
                problems.append(f"{label}: missing '{key}'.")
        if "purpose" in entry and not hqlib.is_text(entry.get("purpose")):
            problems.append(f"{label}: 'purpose' must be a sentence saying what the repo is for.")
        deploys = entry.get("main_deploys_to_production")
        if "main_deploys_to_production" in entry and not isinstance(deploys, bool):
            problems.append(
                f"{label}: 'main_deploys_to_production' must be true or false so agents know "
                "whether pushing main is a production release."
            )
        uses = entry.get("uses")
        if uses is not None:
            if not isinstance(uses, list) or not all(hqlib.is_text(u) for u in uses):
                problems.append(f"{label}: 'uses' must be a list of repo names this repo depends on.")
            else:
                for used in uses:
                    if used == repo.name:
                        problems.append(f"{label}: 'uses' lists itself.")
                    elif used not in raw_repos:
                        problems.append(f"{label}: 'uses' names '{used}', which is not a registered repo.")
        if repo.path in seen_paths:
            problems.append(f"{label}: uses the same folder as repo '{seen_paths[repo.path]}' ({repo.path}).")
        seen_paths[repo.path] = repo.name

        if not repo.path.is_dir():
            problems.append(f"{label}: the folder it points at does not exist: {repo.path}")
            continue
        if not (repo.path / ".git").exists():
            problems.append(f"{label}: {repo.path} is not a git repository.")
        if repo.path == root.resolve():
            problems.append(f"{label}: points at headquarters itself. Register only the repos HQ routes work to.")

        if "rules_file" not in entry:
            problems.append(
                f"{label}: missing 'rules_file'. Use the file workers must follow there "
                "(usually AGENTS.md), or null if the repo has none yet."
            )
        elif entry.get("rules_file") is None:
            notes.append(
                f"{label}: rules_file is null, so workers there have no local rules on its main line. "
                "If a rules file is waiting on an unmerged branch, keep null until the operator merges it "
                "(docs/STATUS.md should name that branch). Otherwise templates/owner-repo/AGENTS.md is a "
                "starting point; ask before adding it."
            )
        elif not hqlib.is_text(entry.get("rules_file")):
            problems.append(f"{label}: 'rules_file' must be a file path or null.")
        elif not (repo.path / str(entry["rules_file"])).is_file():
            problems.append(
                f"{label}: the registry says workers follow {entry['rules_file']}, but that file "
                f"does not exist in {repo.path}."
            )
        status_file = entry.get("status_file")
        if status_file is not None:
            if not hqlib.is_text(status_file):
                problems.append(f"{label}: 'status_file' must be a file path or null.")
            elif not (repo.path / str(status_file)).is_file():
                problems.append(f"{label}: status_file {status_file} does not exist in {repo.path}.")

    groups = data.get("groups")
    if groups is not None:
        if not isinstance(groups, dict):
            problems.append("'groups' must list group names, each with a list of repo names.")
        else:
            for group, members in groups.items():
                if not isinstance(members, list) or not all(hqlib.is_text(m) for m in members):
                    problems.append(f"group '{group}': must be a list of repo names.")
                    continue
                for member in members:
                    if member not in raw_repos:
                        problems.append(f"group '{group}': '{member}' is not a registered repo.")
    return problems, notes


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    args = parser.parse_args(argv)
    try:
        root = hqlib.find_root(args.root)
        problems, notes = check_registry(root)
        count = len(hqlib.registered_repos(root))
    except hqlib.HQError as exc:
        print(f"Registry check could not run: {exc}")
        return 2
    print(f"Registry: {root / hqlib.REGISTRY_FILE}")
    print(f"Repos registered: {count}")
    for note in notes:
        print(f"Note: {note}")
    if problems:
        print(f"Problems: {len(problems)}")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Problems: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
