"""Rule 2: one registry says who owns what."""

from __future__ import annotations

from conftest import make_git_repo, run_ops, write_registry

import hqlib
import validate_registry

GOOD = (
    "repos:\n"
    "  app:\n"
    '    path: "app"\n'
    '    purpose: "The web app."\n'
    '    rules_file: "AGENTS.md"\n'
    "    main_deploys_to_production: true\n"
)


def test_valid_registry_passes(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, GOOD)
    problems, _ = validate_registry.check_registry(hq)
    assert problems == []
    result = run_ops("validate_registry.py", root=hq)
    assert result.returncode == 0, result.stdout
    assert "Problems: 0" in result.stdout


def test_missing_repo_is_reported(hq):
    write_registry(hq, GOOD)
    problems, _ = validate_registry.check_registry(hq)
    assert any("does not exist" in p and "'app'" in p for p in problems)
    result = run_ops("validate_registry.py", root=hq)
    assert result.returncode == 1
    assert "does not exist" in result.stdout


def test_folder_that_is_not_a_git_repo_is_reported(hq):
    (hq.parent / "repos" / "app").mkdir()
    (hq.parent / "repos" / "app" / "AGENTS.md").write_text("rules\n")
    write_registry(hq, GOOD)
    problems, _ = validate_registry.check_registry(hq)
    assert any("not a git repository" in p for p in problems)


def test_release_rule_must_be_true_or_false(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, GOOD.replace("main_deploys_to_production: true", "main_deploys_to_production: ask-the-operator"))
    problems, _ = validate_registry.check_registry(hq)
    assert any("must be true or false" in p for p in problems)


def test_missing_release_rule_and_purpose_are_reported(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, 'repos:\n  app:\n    path: "app"\n    rules_file: "AGENTS.md"\n')
    problems, _ = validate_registry.check_registry(hq)
    assert any("missing 'purpose'" in p for p in problems)
    assert any("missing 'main_deploys_to_production'" in p for p in problems)


def test_rules_file_that_does_not_exist_is_reported(hq):
    make_git_repo(hq.parent / "repos" / "app")
    write_registry(hq, GOOD)
    problems, _ = validate_registry.check_registry(hq)
    assert any("AGENTS.md, but that file does not exist" in p for p in problems)


def test_null_rules_file_is_a_note_not_a_failure(hq):
    make_git_repo(hq.parent / "repos" / "app")
    write_registry(hq, GOOD.replace('rules_file: "AGENTS.md"', "rules_file: null"))
    problems, notes = validate_registry.check_registry(hq)
    assert problems == []
    assert any("rules_file is null" in n and "unmerged branch" in n for n in notes)


def test_rules_file_only_on_an_unmerged_branch_fails_when_registered(hq):
    """The setup hazard: AGENTS.md exists only on a side branch, not the checked-out one."""
    import subprocess

    from conftest import GIT

    repo = make_git_repo(hq.parent / "repos" / "app")
    run = lambda *a: subprocess.run(GIT + list(a), cwd=repo, check=True, capture_output=True, env=hqlib.git_env())  # noqa: E731
    start = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    run("checkout", "-q", "-b", "add-agent-rules")
    (repo / "AGENTS.md").write_text("rules\n")
    run("add", "AGENTS.md")
    run("commit", "-q", "--no-verify", "-m", "Add rules")
    run("checkout", "-q", start)
    write_registry(hq, GOOD)
    problems, _ = validate_registry.check_registry(hq)
    assert any("AGENTS.md, but that file does not exist" in p for p in problems)
    write_registry(hq, GOOD.replace('rules_file: "AGENTS.md"', "rules_file: null"))
    problems, notes = validate_registry.check_registry(hq)
    assert problems == []
    assert any("unmerged branch" in n for n in notes)


def test_group_member_must_be_registered(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, GOOD, "groups:\n  web:\n    - app\n    - api\n")
    problems, _ = validate_registry.check_registry(hq)
    assert problems == ["group 'web': 'api' is not a registered repo."]


def test_typo_in_a_setting_is_reported(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, GOOD + "    purpse: typo\n")
    problems, _ = validate_registry.check_registry(hq)
    assert any("unknown setting 'purpse'" in p for p in problems)


def test_shipped_empty_registry_passes_with_a_setup_note(hq):
    problems, notes = validate_registry.check_registry(hq)
    assert problems == []
    assert any("Set up my headquarters" in n for n in notes)
    assert hqlib.registered_repos(hq) == []


def test_discover_drafts_entries_that_fail_until_the_release_rule_is_answered(hq):
    repos = hq.parent / "repos"
    make_git_repo(repos / "app", {"README.md": "# app\n\nThe web app.\n", "AGENTS.md": "rules\n", "vercel.json": "{}\n"})
    make_git_repo(repos / "notes", {"README.md": "Notes.\n"})
    (repos / "not-a-repo").mkdir()
    draft = hqlib.discover(repos, hq)
    data = hqlib.parse_yaml(draft)
    assert set(data["repos"]) == {"app", "notes"}
    assert data["repos"]["app"]["purpose"] == "The web app."
    assert data["repos"]["app"]["rules_file"] == "AGENTS.md"
    assert data["repos"]["notes"]["rules_file"] is None
    assert data["repos"]["app"]["main_deploys_to_production"] == "ask-the-operator"
    assert "vercel.json" in draft
    write_registry(hq, "repos:\n" + draft.split("repos:\n", 1)[1] + "\n")
    problems, _ = validate_registry.check_registry(hq)
    assert sum("must be true or false" in p for p in problems) == 2


def test_uses_must_name_a_registered_repo(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, GOOD + "    uses:\n      - api\n")
    problems, _ = validate_registry.check_registry(hq)
    assert problems == ["repo 'app': 'uses' names 'api', which is not a registered repo."]


def test_uses_naming_a_registered_repo_passes(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    make_git_repo(hq.parent / "repos" / "api", {"AGENTS.md": "rules\n"})
    api = (
        "  api:\n"
        '    path: "api"\n'
        '    purpose: "The API."\n'
        '    rules_file: "AGENTS.md"\n'
        "    main_deploys_to_production: false\n"
    )
    write_registry(hq, GOOD + "    uses:\n      - api\n" + api)
    problems, _ = validate_registry.check_registry(hq)
    assert problems == []
