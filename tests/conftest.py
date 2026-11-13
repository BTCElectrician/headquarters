"""Shared fixtures. Every test builds its own headquarters in a temporary folder."""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

STARTER = Path(__file__).resolve().parent.parent
OPS = STARTER / "ops"
sys.path.insert(0, str(OPS))
sys.path.insert(0, str(STARTER / "examples" / "three-repo-shop"))

import hqlib  # noqa: E402

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


def make_git_repo(path: Path, files: dict | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for rel, text in (files or {"README.md": "A test repo.\n"}).items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    for step in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "start"]):
        subprocess.run(GIT + step, cwd=path, check=True, env=hqlib.git_env())
    return path


def copy_starter(dest: Path) -> Path:
    """Copy the shipped starter (not the examples or tests) into dest."""
    dest.mkdir(parents=True)
    for item in ("AGENTS.md", "CLAUDE.md", "SETUP.md", "README.md", "LICENSE", "hq.yaml"):
        shutil.copy2(STARTER / item, dest / item)
    for folder in ("docs", "templates", "ops"):
        shutil.copytree(STARTER / folder, dest / folder, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def run(args: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=hqlib.git_env())


def run_ops(script: str, *args: str, root: Path) -> subprocess.CompletedProcess:
    path = OPS / script
    if script.endswith(".sh"):
        return run(["bash", str(path), *args, "--root", str(root)])
    return run([sys.executable, str(path), *args, "--root", str(root)])


@pytest.fixture
def today() -> dt.date:
    return dt.date.today()


@pytest.fixture
def hq(tmp_path: Path) -> Path:
    """A fresh copy of the shipped starter, with a repos/ folder beside it."""
    root = copy_starter(tmp_path / "hq")
    (tmp_path / "repos").mkdir()
    registry = root / "hq.yaml"
    registry.write_text(registry.read_text().replace('repos_root: ".."', 'repos_root: "../repos"'))
    return root


def write_registry(root: Path, repos_yaml: str, groups_yaml: str = "groups: {}\n") -> None:
    (root / "hq.yaml").write_text(
        'hq:\n  name: "Test HQ"\n  repos_root: "../repos"\n' + repos_yaml + groups_yaml
    )


def replace_block(path: Path, start: str, end: str, yaml_text: str) -> None:
    text = path.read_text()
    before = text.split(start, 1)[0]
    after = text.split(end, 1)[1]
    path.write_text(f"{before}{start}\n```yaml\n{yaml_text}```\n{end}{after}")


@pytest.fixture(scope="session")
def example(tmp_path_factory) -> Path:
    import materialize

    target = tmp_path_factory.mktemp("example") / "shop"
    materialize.materialize(target)
    return target


@pytest.fixture(scope="session")
def broken_example(tmp_path_factory) -> Path:
    import materialize

    target = tmp_path_factory.mktemp("broken") / "shop"
    materialize.materialize(target, broken=True)
    return target
