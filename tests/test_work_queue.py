"""Rule 3: permission lives in one place, and only an active approved lane grants it."""

from __future__ import annotations

from conftest import make_git_repo, replace_block, run_ops, write_registry

import validate_work_queue as wq

START, END = wq.START, wq.END

ACTIVE = """\
  - id: build-search
    status: active
    lane_type: implementation
    owner_repos: [app]
    authority: approved
    activation_record: "Operator approved on 2026-11-12 in chat; app only."
    next_action: "Add the search box."
    last_verified: 2026-11-12
"""

QUEUED = """\
  - id: dark-mode
    status: queued
    lane_type: implementation
    owner_repos: [app]
    authority: planning_only
    activation_gate: "Operator approves the plan."
    next_action: "Write the plan."
    last_verified: 2026-11-12
"""


def queue(*lanes: str) -> dict:
    import hqlib

    return hqlib.parse_yaml("schema_version: work_queue.v1\nlanes:\n" + "".join(lanes))


def test_valid_queue_passes_and_only_the_active_approved_lane_authorizes():
    data = queue(ACTIVE, QUEUED)
    assert wq.check_queue(data, ["app"]) == []
    assert [lane["id"] for lane in wq.authorizing_lanes(data)] == ["build-search"]
    assert [lane["id"] for lane in wq.authorizing_lanes(data, "app")] == ["build-search"]
    assert wq.authorizing_lanes(data, "other") == []


def test_queued_lane_never_authorizes_even_with_a_detailed_plan():
    data = queue(QUEUED.replace('next_action: "Write the plan."', 'next_action: "Build dark mode now; the plan is complete."'))
    assert wq.check_queue(data, ["app"]) == []
    assert wq.authorizing_lanes(data) == []


def test_queued_lane_claiming_approval_is_a_violation_and_still_not_permission():
    data = queue(QUEUED.replace("authority: planning_only", "authority: approved"))
    problems = wq.check_queue(data, ["app"])
    assert any("queued lane cannot carry approved authority" in p for p in problems)
    assert wq.authorizing_lanes(data) == []


def test_active_lane_without_approval_is_a_violation_and_not_permission():
    data = queue(ACTIVE.replace("authority: approved", "authority: planning_only"))
    problems = wq.check_queue(data, ["app"])
    assert any("does not have approved authority" in p for p in problems)
    assert wq.authorizing_lanes(data) == []


def test_active_lane_without_activation_record_is_a_violation_and_not_permission():
    lane = "".join(line + "\n" for line in ACTIVE.splitlines() if "activation_record" not in line)
    data = queue(lane)
    problems = wq.check_queue(data, ["app"])
    assert any("needs an activation_record" in p for p in problems)
    assert wq.authorizing_lanes(data) == []


def test_research_lane_never_authorizes_building():
    data = queue(ACTIVE.replace("lane_type: implementation", "lane_type: research").replace("authority: approved", "authority: planning_only"))
    assert wq.check_queue(data, ["app"]) == []
    assert wq.authorizing_lanes(data) == []


def test_lane_for_unregistered_repo_is_a_violation():
    problems = wq.check_queue(queue(ACTIVE), ["something-else"])
    assert any("not registered in hq.yaml" in p for p in problems)


def test_two_active_build_lanes_in_one_repo_need_parallel_approval():
    second = ACTIVE.replace("build-search", "build-filters")
    problems = wq.check_queue(queue(ACTIVE, second), ["app"])
    assert any("2 active implementation lanes" in p for p in problems)
    approved = (ACTIVE + "    parallel_approved: true\n", second + "    parallel_approved: true\n")
    assert wq.check_queue(queue(*approved), ["app"]) == []


def test_finished_lane_must_be_closed_with_evidence():
    done = ACTIVE.replace("status: active", "status: complete")
    problems = wq.check_queue(queue(done), ["app"])
    assert any("must have authority 'closed'" in p for p in problems)
    assert any("needs completion_evidence" in p for p in problems)


def test_blocked_lane_must_say_what_blocks_it():
    blocked = QUEUED.replace("status: queued", "status: blocked")
    problems = wq.check_queue(queue(blocked), ["app"])
    assert any("must list what blocks it" in p for p in problems)


def test_command_line_reports_permission_and_violations(hq):
    make_git_repo(hq.parent / "repos" / "app", {"AGENTS.md": "rules\n"})
    write_registry(hq, 'repos:\n  app:\n    purpose: "App."\n    rules_file: "AGENTS.md"\n    main_deploys_to_production: false\n')
    path = hq / wq.QUEUE_PATH
    replace_block(path, START, END, "schema_version: work_queue.v1\nlanes:\n" + ACTIVE + QUEUED)
    ok = run_ops("validate_work_queue.py", "--authorized", root=hq)
    assert ok.returncode == 0, ok.stdout
    assert "build-search" in ok.stdout and "dark-mode" not in ok.stdout.split("Lanes that authorize")[1]

    replace_block(path, START, END, "schema_version: work_queue.v1\nlanes:\n" + QUEUED.replace("planning_only", "approved"))
    bad = run_ops("validate_work_queue.py", "--authorized", root=hq)
    assert bad.returncode == 1
    assert "treat no lane in this file as permission" in bad.stdout


def test_broken_markers_stop_the_check(hq):
    path = hq / wq.QUEUE_PATH
    path.write_text(path.read_text().replace(END, ""))
    result = run_ops("validate_work_queue.py", root=hq)
    assert result.returncode == 2
    assert "marker lines" in result.stdout
