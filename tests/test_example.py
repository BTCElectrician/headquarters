"""The three-repo example runs the whole loop, and its broken variant is caught."""

from __future__ import annotations

import subprocess

from conftest import run_ops

import materialize


def _git_state(repo):
    return subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout


def test_example_builds_real_repos_and_every_check_passes(example):
    hq = example / "headquarters"
    for name in materialize.REPOS:
        assert (example / "repos" / name / ".git").is_dir()
    assert (hq / ".git").is_dir()
    before = {name: _git_state(example / "repos" / name) for name in materialize.REPOS}

    result = run_ops("check_all.sh", root=hq)
    assert result.returncode == 0, result.stdout
    assert "All checks passed." in result.stdout
    assert "shop-docs': rules_file is null" in result.stdout
    assert "keep null until the operator merges it" in result.stdout

    status = run_ops("status_all.sh", root=hq)
    assert status.returncode == 0
    assert "dirty:1" in status.stdout

    allowed = run_ops("validate_work_queue.py", "--authorized", root=hq)
    tail = allowed.stdout.split("Lanes that authorize implementation:")[1]
    assert "order-lookup-by-email" in tail and "refund-button" not in tail

    waiting = run_ops("operator_decisions.py", "list", root=hq)
    assert "refund-button-scope" in waiting.stdout and "Recommendation: Full refunds only" in waiting.stdout

    code = run_ops("repo_context.py", "--repo", "shop-api", "--terms", "create order", root=hq)
    assert code.returncode == 0 and "api/orders.py" in code.stdout
    plan = run_ops("repo_context.py", "--repo", "shop-api", "--terms", "refund", root=hq)
    assert "shows intent, not a working feature" in plan.stdout

    after = {name: _git_state(example / "repos" / name) for name in materialize.REPOS}
    assert before == after, "the scripts must never change the registered repos"


def test_broken_example_is_caught_by_every_check(broken_example):
    hq = broken_example / "headquarters"
    registry = run_ops("validate_registry.py", root=hq)
    assert registry.returncode == 1 and "shop-mobile" in registry.stdout
    queue = run_ops("validate_work_queue.py", root=hq)
    assert queue.returncode == 1 and "queued lane cannot carry approved authority" in queue.stdout
    decisions = run_ops("operator_decisions.py", "validate", root=hq)
    assert decisions.returncode == 1 and "has no recommendation" in decisions.stdout
    docs = run_ops("validate_docs.py", root=hq)
    assert docs.returncode == 1
    assert "OLD_LAUNCH_PLAN.md: orphaned" in docs.stdout and "STATUS.md: stale" in docs.stdout
    status = run_ops("status_all.sh", root=hq)
    assert status.returncode == 1 and "MISSING" in status.stdout
    combined = run_ops("check_all.sh", root=hq)
    assert combined.returncode == 1 and "4 check(s) found problems" in combined.stdout


def test_materialize_refuses_a_folder_that_is_not_empty(tmp_path):
    (tmp_path / "keep.txt").write_text("mine\n")
    try:
        materialize.materialize(tmp_path)
    except SystemExit as exc:
        assert "not empty" in str(exc)
    else:
        raise AssertionError("materialize wrote into a non-empty folder")
    assert [p.name for p in tmp_path.iterdir()] == ["keep.txt"]


def test_git_hook_variables_cannot_redirect_writes(tmp_path, monkeypatch):
    """Inside a git hook, GIT_DIR points at the hook's repo. The example must ignore it."""
    decoy = tmp_path / "decoy"
    subprocess.run(["git", "init", "-q", str(decoy)], check=True)
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git" / "index"))
    target = materialize.materialize(tmp_path / "shop")
    assert (target / "repos" / "shop-api" / ".git").is_dir()
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_INDEX_FILE")
    log = subprocess.run(["git", "log", "--oneline"], cwd=decoy, capture_output=True, text=True)
    assert log.returncode != 0 or log.stdout == ""
