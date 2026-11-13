#!/usr/bin/env python3
"""List or check the decisions waiting on the operator (docs/OPERATOR_DECISIONS.md).

  python3 ops/operator_decisions.py list       what is waiting, most urgent first
  python3 ops/operator_decisions.py validate   fail if any entry is not prepared

An open entry must carry the question, a recommendation, the reason for it,
what answering it unblocks, and a link to the prepared work. Agents edit the
YAML block in the Markdown file by hand; this script only reads it.

Exit codes: 0 = fine, 1 = problems found, 2 = could not run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hqlib  # noqa: E402

DOC_PATH = "docs/OPERATOR_DECISIONS.md"
START = "<!-- operator-decisions:start -->"
END = "<!-- operator-decisions:end -->"
SCHEMA = "operator_decisions.v1"
STATUSES = {"open", "answered", "done", "deferred", "withdrawn"}
IMPACT_ORDER = ["outside", "money", "unblock", "internal"]
STALE_DAYS = 14
SHOW_IN_FULL = 3
SHOW_AT_ALL = 10
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

ALWAYS = ("id", "status", "question", "recommendation", "why", "unblocks", "owner", "minutes", "impact", "opened", "last_checked")
BY_STATUS = {
    "open": ("prepared",),
    "answered": ("answer", "answered_on"),
    "done": ("closed_on",),
    "deferred": ("deferred_reason", "deferred_on"),
    "withdrawn": ("closed_on",),
}
DATE_FIELDS = ("opened", "last_checked", "answered_on", "deferred_on", "closed_on", "due")


def load_decisions(root: Path) -> Dict[str, Any]:
    path = root / DOC_PATH
    if not path.is_file():
        raise hqlib.HQError(f"{DOC_PATH} is missing")
    data = hqlib.load_marked_yaml(path, START, END)
    if not isinstance(data, dict):
        raise hqlib.HQError(f"{DOC_PATH}: the decisions block must start with 'schema_version:'")
    return data


def check_decisions(data: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if data.get("schema_version") != SCHEMA:
        problems.append(f"schema_version must be '{SCHEMA}'.")
    entries = data.get("decisions")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        return problems + ["'decisions' must be a list (use [] when nothing is waiting)."]
    seen: set = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"entry #{index + 1}: must be a set of 'key: value' fields.")
            continue
        entry_id = entry.get("id")
        label = f"'{entry_id}'" if hqlib.is_text(entry_id) else f"entry #{index + 1}"
        if hqlib.is_text(entry_id):
            if not ID_RE.match(entry_id):
                problems.append(f"{label}: id must be lowercase words joined by hyphens.")
            if entry_id in seen:
                problems.append(f"{label}: the id is used twice.")
            seen.add(entry_id)
        status = entry.get("status")
        if status not in STATUSES:
            problems.append(f"{label}: status '{status}' is not one of {', '.join(sorted(STATUSES))}.")
        required = list(ALWAYS) + list(BY_STATUS.get(status, ()))
        if status == "done" and entry.get("answer") is not None:
            required += ["answered_on"]
        for field in required:
            value = entry.get(field)
            if field in DATE_FIELDS or field == "minutes":
                if value is None:
                    problems.append(f"{label}: '{field}' is required for a {status} entry.")
                continue
            if not hqlib.is_text(value):
                if field == "recommendation":
                    problems.append(
                        f"{label}: has no recommendation. Every entry needs the agent's recommended answer."
                    )
                elif field == "prepared":
                    problems.append(
                        f"{label}: is open but has no 'prepared' link. Finish the preparation "
                        "(preview, test, draft) before asking the operator."
                    )
                else:
                    problems.append(f"{label}: '{field}' is required and cannot be empty for a {status} entry.")
        if entry.get("impact") is not None and entry.get("impact") not in IMPACT_ORDER:
            problems.append(f"{label}: impact must be one of {', '.join(IMPACT_ORDER)}.")
        minutes = entry.get("minutes")
        if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0):
            problems.append(f"{label}: 'minutes' must be a whole number above zero (honest operator time).")
        for field in DATE_FIELDS:
            value = entry.get(field)
            if value is not None and hqlib.as_date(value) is None:
                problems.append(f"{label}: '{field}' must be a date written as YYYY-MM-DD.")
    return problems


def _rank(entry: Dict[str, Any]) -> tuple:
    due = hqlib.as_date(entry.get("due"))
    impact = entry.get("impact")
    impact_rank = IMPACT_ORDER.index(impact) if impact in IMPACT_ORDER else len(IMPACT_ORDER)
    opened = hqlib.as_date(entry.get("opened")) or dt.date.max
    return (0 if due else 1, due or dt.date.max, impact_rank, opened, str(entry.get("id")))


def _flat(value: Any) -> str:
    return " ".join(str(value).split())


def _stale(entry: Dict[str, Any], today: dt.date) -> str:
    checked = hqlib.as_date(entry.get("last_checked"))
    if checked and (today - checked).days > STALE_DAYS:
        return f" (not rechecked since {checked.isoformat()})"
    return ""


def render(data: Dict[str, Any], today: dt.date, show_every: bool = False, include_deferred: bool = False) -> str:
    entries = [e for e in (data.get("decisions") or []) if isinstance(e, dict)]
    waiting = sorted((e for e in entries if e.get("status") == "open"), key=_rank)
    out: List[str] = []
    if not waiting:
        out.append("Nothing is waiting on you.")
    else:
        out.append(f"Waiting on you: {len(waiting)}")
        full = len(waiting) if show_every else SHOW_IN_FULL
        for entry in waiting[:full]:
            out.append("")
            out.append(f"{entry['id']}{_stale(entry, today)}")
            out.append(f"  Question: {_flat(entry['question'])}")
            out.append(f"  Recommendation: {_flat(entry['recommendation'])}")
            out.append(f"  Why: {_flat(entry['why'])}")
            out.append(f"  Unblocks: {_flat(entry['unblocks'])}")
            out.append(f"  Prepared work: {_flat(entry['prepared'])}")
            due = hqlib.as_date(entry.get("due"))
            timing = f"About {entry['minutes']} min of your time"
            if due:
                timing += f" | Due {due.isoformat()}"
            out.append(f"  {timing} | Follow-through: {_flat(entry['owner'])}")
        if not show_every:
            rest = waiting[SHOW_IN_FULL:SHOW_AT_ALL]
            if rest:
                out.append("")
                out.append("Also waiting:")
                for entry in rest:
                    out.append(f"- {entry['id']}: {_flat(entry['question'])} (about {entry['minutes']} min){_stale(entry, today)}")
            if len(waiting) > SHOW_AT_ALL:
                out.append(f"... and {len(waiting) - SHOW_AT_ALL} more in {DOC_PATH}.")
    answered = [str(e.get("id")) for e in entries if e.get("status") == "answered"]
    if answered:
        out.append("")
        out.append(f"Answered, follow-through not finished: {', '.join(answered)}")
    if include_deferred:
        deferred = [e for e in entries if e.get("status") == "deferred"]
        if deferred:
            out.append("")
            out.append("Deferred (recorded, not reminders):")
            for entry in deferred:
                out.append(f"- {entry.get('id')}: {_flat(entry.get('question'))} Reason: {_flat(entry.get('deferred_reason'))}")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["list", "validate"])
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    parser.add_argument("--today", help="pretend today is this date (YYYY-MM-DD); useful in tests")
    parser.add_argument("--every", action="store_true", help="show every open entry in full")
    parser.add_argument("--deferred", action="store_true", help="also show deferred entries")
    args = parser.parse_args(argv)
    try:
        today = hqlib.parse_today(args.today)
        root = hqlib.find_root(args.root)
        data = load_decisions(root)
    except hqlib.HQError as exc:
        print(f"Operator decisions could not be read: {exc}")
        return 2
    problems = check_decisions(data)
    if problems:
        print(f"Operator decisions have {len(problems)} problem(s) in {DOC_PATH}:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    if args.command == "validate":
        entries = data.get("decisions") or []
        waiting = sum(1 for e in entries if isinstance(e, dict) and e.get("status") == "open")
        print(f"Operator decisions: {len(entries)} entries, {waiting} waiting. Problems: 0")
        return 0
    print(render(data, today, args.every, args.deferred))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
