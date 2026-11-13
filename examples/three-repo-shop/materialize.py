#!/usr/bin/env python3
"""Build the three-repo shop example in a folder of your choice.

  python3 examples/three-repo-shop/materialize.py /tmp/shop-example
  python3 examples/three-repo-shop/materialize.py /tmp/shop-broken --broken

Creates, inside the target folder:

  repos/shop-app    a tiny storefront (git repo, one commit, one uncommitted edit)
  repos/shop-api    a tiny orders API (git repo, one commit)
  repos/shop-docs   a tiny help site (git repo, one commit, no rules file)
  headquarters/     a copy of this starter with the example registry, status,
                    work queue and decisions filled in (also a git repo)

--broken plants five known problems so you can watch the checks catch them:
a registered repo that does not exist, a queued lane that claims approval, an
open decision with no recommendation, an orphaned doc, and a stale status file.

It only writes inside the target folder, which must be empty or not exist yet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
STARTER = HERE.parent.parent
sys.path.insert(0, str(STARTER / "ops"))

import hqlib  # noqa: E402
STARTER_ITEMS = ("AGENTS.md", "CLAUDE.md", "SETUP.md", "README.md", "LICENSE", ".gitignore", "hq.yaml", "docs", "templates", "ops")
REPOS = ("shop-app", "shop-api", "shop-docs")
GIT_IDENTITY = [
    "-c", "user.name=Example Shop",
    "-c", "user.email=example@example.com",
    "-c", "commit.gpgsign=false",
    "-c", "init.defaultBranch=main",
]


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], cwd=folder, check=True, capture_output=True, env=hqlib.git_env())


def init_repo(folder: Path, message: str) -> None:
    git(folder, "init", "-q")
    git(folder, "symbolic-ref", "HEAD", "refs/heads/main")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "--no-verify", "-m", message)


def fill_dates(folder: Path, today: str) -> None:
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".yaml", ".py", ".js"}:
            text = path.read_text(encoding="utf-8")
            if "{{TODAY}}" in text:
                path.write_text(text.replace("{{TODAY}}", today), encoding="utf-8")


def copy_starter(target: Path) -> None:
    target.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in STARTER_ITEMS:
        source = STARTER / item
        if source.is_dir():
            shutil.copytree(source, target / item, ignore=ignore)
        elif source.is_file():
            shutil.copy2(source, target / item)


def plant_problems(root: Path, today: dt.date) -> None:
    hq = root / "headquarters"
    registry = hq / "hq.yaml"
    text = registry.read_text(encoding="utf-8")
    text = text.replace(
        "\ngroups:",
        "\n  shop-mobile:\n"
        '    path: "shop-mobile"\n'
        '    purpose: "A mobile app that was planned but never cloned here."\n'
        '    rules_file: "AGENTS.md"\n'
        "    main_deploys_to_production: false\n"
        "\ngroups:",
        1,
    )
    registry.write_text(text, encoding="utf-8")

    queue = hq / "docs" / "WORK_QUEUE.md"
    text = queue.read_text(encoding="utf-8")
    text = text.replace(
        "    authority: planning_only\n",
        "    authority: approved\n",
        1,
    )
    queue.write_text(text, encoding="utf-8")

    decisions = hq / "docs" / "OPERATOR_DECISIONS.md"
    text = decisions.read_text(encoding="utf-8")
    text = text.replace(
        "    recommendation: Full refunds only for the first version.\n",
        "",
        1,
    )
    decisions.write_text(text, encoding="utf-8")

    stale_day = (today - dt.timedelta(days=30)).isoformat()
    (hq / "docs" / "OLD_LAUNCH_PLAN.md").write_text(
        f"<!-- reviewed: {stale_day} | review every: as needed -->\n"
        "# Launch plan from last spring\n\n"
        "An old plan that nothing links to any more.\n",
        encoding="utf-8",
    )
    status = hq / "docs" / "STATUS.md"
    lines = status.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[0] = f"<!-- reviewed: {stale_day} | review every: 7 days -->\n"
    status.write_text("".join(lines), encoding="utf-8")


def materialize(target: Path, broken: bool = False, today: Optional[dt.date] = None) -> Path:
    today = today or dt.date.today()
    target = target.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty. Choose a new or empty folder.")
    target.mkdir(parents=True, exist_ok=True)

    repos = target / "repos"
    for name in REPOS:
        shutil.copytree(HERE / "repos" / name, repos / name)
        fill_dates(repos / name, today.isoformat())
        init_repo(repos / name, f"Start {name}")
    # A dirty repo is normal while someone works; status_all.sh shows it as a signal.
    with (repos / "shop-app" / "src" / "cart.js").open("a", encoding="utf-8") as handle:
        handle.write("// work in progress: free-shipping banner\n")

    hq = target / "headquarters"
    copy_starter(hq)
    for path in (HERE / "hq").rglob("*"):
        if path.is_file():
            destination = hq / path.relative_to(HERE / "hq")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    fill_dates(hq / "docs", today.isoformat())
    if broken:
        plant_problems(target, today)
    init_repo(hq, "Example headquarters for the three-repo shop")
    return target


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="folder to create the example in (new or empty)")
    parser.add_argument("--broken", action="store_true", help="plant known problems for the checks to catch")
    args = parser.parse_args(argv)
    try:
        target = materialize(Path(args.target), broken=args.broken)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip() if exc.stderr else str(exc)
        print(f"A git command failed while building the example: {detail}", file=sys.stderr)
        return 2
    hq = target / "headquarters"
    print(f"Example built in {target}")
    print("")
    print("Try:")
    print(f"  cd {hq}")
    print("  ops/status_all.sh")
    print("  ops/check_all.sh")
    print("  python3 ops/repo_context.py --repo shop-api --terms \"create order\"")
    print("  python3 ops/operator_decisions.py list")
    print("  python3 ops/validate_work_queue.py --authorized")
    print("")
    print("Or open Claude Code or Codex in that folder and ask it to route a task.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
