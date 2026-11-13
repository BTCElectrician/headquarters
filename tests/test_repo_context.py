"""Rule 4: look at the live repo before saying what it can do."""

from __future__ import annotations

import subprocess

from conftest import make_git_repo, run_ops, write_registry

REGISTRY = (
    "repos:\n"
    "  api:\n"
    '    purpose: "The API."\n'
    '    rules_file: "AGENTS.md"\n'
    "    main_deploys_to_production: true\n"
)


def _api(hq, with_rules=True):
    files = {
        "src/orders.py": "def create_order(items):\n    return items\n",
        "tests/test_orders.py": "from src.orders import create_order\n",
        "docs/plans/refunds.md": "Refunds are planned.\n",
        "STATUS.md": "Status.\n",
        ".env": "create order secret\n",
    }
    if with_rules:
        files["AGENTS.md"] = "Rules.\n"
    return make_git_repo(hq.parent / "repos" / "api", files)


def test_complete_context_with_code_matches(hq):
    repo = _api(hq)
    write_registry(hq, REGISTRY)
    before = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "create order", root=hq)
    assert result.returncode == 0, result.stdout
    assert "src/orders.py:1" in result.stdout
    assert "tests/test_orders.py:1" in result.stdout
    assert "pushing main deploys to production" in result.stdout
    assert "Minimum live context: complete" in result.stdout
    assert "No code or tests mention" not in result.stdout
    assert ".env" not in result.stdout
    after = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout
    assert before == after


def test_docs_only_match_is_called_intent_not_a_feature(hq):
    _api(hq)
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "refunds", root=hq)
    assert result.returncode == 0
    assert "docs/plans/refunds.md:1" in result.stdout
    assert "No code or tests mention these terms." in result.stdout
    assert "shows intent, not a working feature" in result.stdout


def test_no_matches_does_not_read_like_success(hq):
    _api(hq)
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "loyalty points", root=hq)
    assert result.returncode == 0
    assert "No code or tests mention these terms." in result.stdout
    assert "no matches at all" in result.stdout
    assert "Minimum live context: complete (the rules file, status file and latest commit were readable)." in result.stdout


def test_tests_only_match_says_no_code_mentions_it(hq):
    _api(hq)
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "import create order", root=hq)
    assert "No code mentions these terms; only tests do." in result.stdout


def test_mostly_docs_repo_gets_a_softer_docs_reading(hq):
    files = {f"pages/page{i}.md": f"Page {i} about returns.\n" for i in range(4)}
    files.update({"AGENTS.md": "Rules.\n", "STATUS.md": "Status.\n"})
    make_git_repo(hq.parent / "repos" / "api", files)
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "returns", root=hq)
    assert "No code or tests mention these terms." in result.stdout
    assert "mostly documents" in result.stdout
    assert "shows intent, not a working feature" not in result.stdout


def test_missing_rules_file_makes_context_incomplete(hq):
    _api(hq, with_rules=False)
    write_registry(hq, REGISTRY.replace('rules_file: "AGENTS.md"', "rules_file: null"))
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "create order", root=hq)
    assert result.returncode == 1
    assert "Minimum live context: incomplete" in result.stdout
    assert "a rules file" in result.stdout


def test_unknown_repo_is_refused(hq):
    _api(hq)
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "billing", "--terms", "invoice", root=hq)
    assert result.returncode == 2
    assert "'billing' is not registered" in result.stdout


def test_registered_but_missing_repo_is_refused(hq):
    write_registry(hq, REGISTRY)
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "x", root=hq)
    assert result.returncode == 2
    assert "does not exist" in result.stdout


def test_plain_folder_inside_another_repo_is_refused(hq):
    outer = make_git_repo(hq.parent / "repos" / "outer")
    (outer / "api").mkdir()
    (outer / "api" / "AGENTS.md").write_text("rules\n")
    write_registry(hq, REGISTRY.replace("  api:\n", '  api:\n    path: "outer/api"\n'))
    result = run_ops("repo_context.py", "--repo", "api", "--terms", "x", root=hq)
    assert result.returncode == 2
    assert "not a repository of its own" in result.stdout
