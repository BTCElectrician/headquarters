"""The shipped starter is complete, passes its own checks, and has no leftovers."""

from __future__ import annotations

import os
import re
from pathlib import Path

from conftest import STARTER, run

TREE = [
    "README.md", "SETUP.md", "AGENTS.md", "CLAUDE.md", "hq.yaml", "LICENSE", ".gitignore",
    "docs/STATUS.md", "docs/WORK_QUEUE.md", "docs/OPERATOR_DECISIONS.md", "docs/ROUTING.md",
    "docs/CROSS_REPO_OPERATIONS.md", "docs/MODELS.md", "docs/WHY_HEADQUARTERS.md", "docs/HISTORY.md",
    "templates/owner-repo/AGENTS.md", "templates/owner-repo/STATUS.md", "templates/worker-brief.md",
    "ops/status_all.sh", "ops/repo_context.py", "ops/validate_work_queue.py",
    "ops/operator_decisions.py", "ops/validate_docs.py", "ops/validate_registry.py",
    "ops/check_all.sh", "ops/hqlib.py",
    "examples/three-repo-shop/README.md", "examples/three-repo-shop/materialize.py",
]


def shipped_files():
    for path in sorted(STARTER.rglob("*")):
        rel = path.relative_to(STARTER)
        if path.is_file() and not any(part in {".git", "__pycache__", ".pytest_cache"} for part in rel.parts):
            yield path


def test_every_file_in_the_outline_exists():
    missing = [rel for rel in TREE if not (STARTER / rel).is_file()]
    assert missing == []


def test_scripts_are_executable():
    for rel in TREE:
        if rel.startswith("ops/") and rel != "ops/hqlib.py":
            assert os.access(STARTER / rel, os.X_OK), rel


def test_no_placeholder_filler_left_in_shipped_files():
    pattern = re.compile(r"\b(TODO|FIXME|TBD|lorem ipsum)\b", re.IGNORECASE)
    hits = []
    for path in shipped_files():
        if path.suffix not in {".md", ".py", ".sh", ".yaml", ".js"} or path.name == Path(__file__).name:
            continue
        for number, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{path.relative_to(STARTER)}:{number}")
    assert hits == []


def test_claude_adapter_imports_agents_file():
    assert (STARTER / "CLAUDE.md").read_text().startswith("@AGENTS.md")


def test_the_starter_itself_passes_every_check():
    result = run(["bash", str(STARTER / "ops" / "check_all.sh")])
    assert result.returncode == 0, result.stdout
    assert "All checks passed." in result.stdout
