"""ops/status_all.sh shows every registered repo and fails on a missing one."""

from __future__ import annotations

from conftest import make_git_repo, run_ops, write_registry

REGISTRY = (
    "repos:\n"
    "  app:\n"
    '    purpose: "App."\n'
    '    rules_file: null\n'
    "    main_deploys_to_production: true\n"
    "  api:\n"
    '    purpose: "API."\n'
    '    rules_file: null\n'
    "    main_deploys_to_production: false\n"
)


def test_reports_clean_and_dirty_repos(hq):
    make_git_repo(hq.parent / "repos" / "app")
    api = make_git_repo(hq.parent / "repos" / "api")
    (api / "new.txt").write_text("work in progress\n")
    write_registry(hq, REGISTRY)
    result = run_ops("status_all.sh", root=hq)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = {line.split()[0]: line for line in result.stdout.splitlines()[2:] if line.strip()}
    assert "clean" in lines["app"] and "main=prod" in lines["app"]
    assert "dirty:1" in lines["api"] and "manual" in lines["api"]


def test_missing_repo_fails_with_a_plain_message(hq):
    make_git_repo(hq.parent / "repos" / "app")
    write_registry(hq, REGISTRY)
    result = run_ops("status_all.sh", root=hq)
    assert result.returncode == 1
    assert "MISSING" in result.stdout
    assert "missing or are not git repositories" in result.stdout


def test_empty_registry_points_to_setup(hq):
    result = run_ops("status_all.sh", root=hq)
    assert result.returncode == 0
    assert "Set up my headquarters" in result.stdout
