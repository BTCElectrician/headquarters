"""Rule 7: decisions arrive prepared."""

from __future__ import annotations

import datetime as dt

from conftest import replace_block, run_ops

import hqlib
import operator_decisions as od

OPEN = """\
  - id: pick-host
    status: open
    question: "Should the app move to the new host this month?"
    recommendation: "Yes, after the staging test."
    why: "The staging run was faster and cheaper."
    unblocks: "The hosting migration lane."
    prepared: "app pull request 12"
    owner: "HQ lead"
    minutes: 5
    impact: money
    opened: 2026-11-01
    last_checked: 2026-11-10
"""


def data(*entries: str) -> dict:
    return hqlib.parse_yaml("schema_version: operator_decisions.v1\ndecisions:\n" + "".join(entries))


def test_prepared_open_entry_passes():
    assert od.check_decisions(data(OPEN)) == []


def test_open_entry_without_recommendation_fails():
    entry = "".join(line + "\n" for line in OPEN.splitlines() if "recommendation" not in line)
    problems = od.check_decisions(data(entry))
    assert problems == ["'pick-host': has no recommendation. Every entry needs the agent's recommended answer."]


def test_open_entry_with_empty_recommendation_fails():
    problems = od.check_decisions(data(OPEN.replace('"Yes, after the staging test."', '""')))
    assert any("has no recommendation" in p for p in problems)


def test_open_entry_without_prepared_work_fails():
    entry = "".join(line + "\n" for line in OPEN.splitlines() if "prepared" not in line)
    problems = od.check_decisions(data(entry))
    assert any("no 'prepared' link" in p for p in problems)


def test_open_entry_missing_reason_or_unblocks_fails():
    entry = "".join(line + "\n" for line in OPEN.splitlines() if not line.strip().startswith(("why", "unblocks")))
    problems = od.check_decisions(data(entry))
    assert any("'why'" in p for p in problems)
    assert any("'unblocks'" in p for p in problems)


def test_answered_entry_needs_the_answer():
    problems = od.check_decisions(data(OPEN.replace("status: open", "status: answered")))
    assert any("'answer'" in p for p in problems)


def test_minutes_must_be_a_positive_whole_number():
    problems = od.check_decisions(data(OPEN.replace("minutes: 5", "minutes: 0")))
    assert any("'minutes'" in p for p in problems)


def test_ranking_puts_due_dates_first_then_impact():
    later = OPEN.replace("pick-host", "internal-thing").replace("impact: money", "impact: internal")
    urgent = OPEN.replace("pick-host", "due-soon").replace("impact: money", "impact: internal") + "    due: 2026-11-20\n"
    outside = OPEN.replace("pick-host", "customer-facing").replace("impact: money", "impact: outside")
    text = od.render(data(later, urgent, outside, OPEN), dt.date(2026, 11, 12), show_every=True)
    order = [line for line in text.splitlines() if line and not line.startswith((" ", "Waiting"))]
    assert order == ["due-soon", "customer-facing", "pick-host", "internal-thing"]


def test_stale_entries_are_marked():
    text = od.render(data(OPEN), dt.date(2026, 12, 31))
    assert "not rechecked since 2026-11-10" in text


def test_empty_list_says_nothing_is_waiting(hq):
    result = run_ops("operator_decisions.py", "list", root=hq)
    assert result.returncode == 0
    assert "Nothing is waiting on you." in result.stdout


def test_command_line_validate_fails_on_unprepared_entry(hq):
    path = hq / od.DOC_PATH
    entry = "".join(line + "\n" for line in OPEN.splitlines() if "recommendation" not in line)
    replace_block(path, od.START, od.END, "schema_version: operator_decisions.v1\ndecisions:\n" + entry)
    for command in ("validate", "list"):
        result = run_ops("operator_decisions.py", command, root=hq)
        assert result.returncode == 1
        assert "has no recommendation" in result.stdout
