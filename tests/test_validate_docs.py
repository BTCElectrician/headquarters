"""Stale, orphaned and broken headquarters documents are flagged."""

from __future__ import annotations

import datetime as dt

from conftest import run_ops

import validate_docs

TODAY = dt.date(2026, 11, 12)


def test_shipped_docs_pass(hq):
    assert validate_docs.check_docs(hq, TODAY) == []


def test_orphaned_doc_is_flagged(hq):
    (hq / "docs" / "OLD_PLAN.md").write_text("<!-- reviewed: 2026-11-12 | review every: as needed -->\n# Old plan\n")
    problems = validate_docs.check_docs(hq, TODAY)
    assert problems == [problems[0]]
    assert "docs/OLD_PLAN.md: orphaned" in problems[0]


def test_linking_the_doc_fixes_the_orphan(hq):
    (hq / "docs" / "OLD_PLAN.md").write_text("<!-- reviewed: 2026-11-12 | review every: as needed -->\n# Plan\n")
    status = hq / "docs" / "STATUS.md"
    status.write_text(status.read_text() + "\nSee `docs/OLD_PLAN.md`.\n")
    assert validate_docs.check_docs(hq, TODAY) == []


def test_archived_docs_are_not_orphans(hq):
    (hq / "docs" / "archive").mkdir()
    (hq / "docs" / "archive" / "OLD_PLAN.md").write_text("# Old plan, kept as history\n")
    assert validate_docs.check_docs(hq, TODAY) == []


def test_stale_doc_is_flagged_and_fresh_doc_passes(hq):
    status = hq / "docs" / "STATUS.md"
    lines = status.read_text().splitlines(keepends=True)
    lines[0] = "<!-- reviewed: 2026-11-01 | review every: 7 days -->\n"
    status.write_text("".join(lines))
    problems = validate_docs.check_docs(hq, TODAY)
    assert len(problems) == 1 and "docs/STATUS.md: stale" in problems[0]
    lines[0] = "<!-- reviewed: 2026-11-06 | review every: 7 days -->\n"
    status.write_text("".join(lines))
    assert validate_docs.check_docs(hq, TODAY) == []


def test_missing_review_line_is_flagged(hq):
    status = hq / "docs" / "STATUS.md"
    status.write_text("\n".join(status.read_text().splitlines()[1:]) + "\n")
    problems = validate_docs.check_docs(hq, TODAY)
    assert any("missing its review line" in p for p in problems)


def test_broken_link_is_flagged(hq):
    status = hq / "docs" / "STATUS.md"
    status.write_text(status.read_text() + "\nSee [the plan](plans/missing.md).\n")
    problems = validate_docs.check_docs(hq, TODAY)
    assert any("plans/missing.md" in p and "does not exist" in p for p in problems)


def test_startup_file_pointing_into_archive_is_flagged(hq):
    (hq / "docs" / "archive").mkdir()
    (hq / "docs" / "archive" / "OLD.md").write_text("# history\n")
    agents = hq / "AGENTS.md"
    agents.write_text(agents.read_text() + "\nAlso read docs/archive/OLD.md first.\n")
    problems = validate_docs.check_docs(hq, TODAY)
    assert any("sends agents into archived history" in p for p in problems)


def test_command_line_exit_codes(hq):
    assert run_ops("validate_docs.py", "--today", "2026-11-12", root=hq).returncode == 0
    (hq / "docs" / "STRAY.md").write_text("<!-- reviewed: 2026-11-12 | review every: as needed -->\n# Stray\n")
    result = run_ops("validate_docs.py", "--today", "2026-11-12", root=hq)
    assert result.returncode == 1
    assert "orphaned" in result.stdout
