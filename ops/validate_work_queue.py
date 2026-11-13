#!/usr/bin/env python3
"""Check the work queue (docs/WORK_QUEUE.md) and show which lanes grant permission.

A lane authorizes building only when all four of these are true:
  status is active, lane_type is implementation, authority is approved,
  and activation_record says who approved it, when, and for what scope.
Everything else (queued, parked, waiting, blocked, done, or unapproved) is
context, not permission. This check fails when a lane's fields contradict
each other in a way that could read as a go-ahead.

Read-only. Exit codes: 0 = no problems, 1 = problems found, 2 = could not run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hqlib  # noqa: E402

QUEUE_PATH = "docs/WORK_QUEUE.md"
START = "<!-- work-queue:start -->"
END = "<!-- work-queue:end -->"
SCHEMA = "work_queue.v1"

STATUSES = {"active", "queued", "parked", "waiting", "blocked", "complete", "cancelled"}
LANE_TYPES = {"implementation", "coordination", "research"}
AUTHORITIES = {"approved", "planning_only", "none", "closed"}
CLOSED = {"complete", "cancelled"}
NOT_STARTED = {"queued", "parked", "waiting"}
REQUIRED = (
    "id",
    "status",
    "lane_type",
    "owner_repos",
    "authority",
    "next_action",
    "last_verified",
)


def load_queue(root: Path) -> Dict[str, Any]:
    path = root / QUEUE_PATH
    if not path.is_file():
        raise hqlib.HQError(f"{QUEUE_PATH} is missing")
    data = hqlib.load_marked_yaml(path, START, END)
    if not isinstance(data, dict):
        raise hqlib.HQError(f"{QUEUE_PATH}: the work-queue block must start with 'schema_version:'")
    return data


def grants_permission(lane: Dict[str, Any]) -> bool:
    """True only for a lane that authorizes implementation work right now."""
    return (
        lane.get("status") == "active"
        and lane.get("lane_type") == "implementation"
        and lane.get("authority") == "approved"
        and hqlib.is_text(lane.get("activation_record"))
    )


def authorizing_lanes(data: Dict[str, Any], repo: Optional[str] = None) -> List[Dict[str, Any]]:
    lanes = data.get("lanes") or []
    out = [lane for lane in lanes if isinstance(lane, dict) and grants_permission(lane)]
    if repo:
        out = [lane for lane in out if repo in (lane.get("owner_repos") or [])]
    return out


def check_queue(data: Dict[str, Any], registered: Optional[List[str]] = None) -> List[str]:
    problems: List[str] = []
    if data.get("schema_version") != SCHEMA:
        problems.append(f"schema_version must be '{SCHEMA}'.")
    lanes = data.get("lanes")
    if lanes is None:
        lanes = []
    if not isinstance(lanes, list):
        return problems + ["'lanes' must be a list (use [] when there are none)."]

    seen: set = set()
    active_build_lanes: Dict[str, List[str]] = {}
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            problems.append(f"lane #{index + 1}: must be a set of 'key: value' fields.")
            continue
        lane_id = lane.get("id")
        label = f"lane '{lane_id}'" if hqlib.is_text(lane_id) else f"lane #{index + 1}"
        if hqlib.is_text(lane_id):
            if lane_id in seen:
                problems.append(f"{label}: the id is used twice.")
            seen.add(lane_id)
        for field in REQUIRED:
            if field not in lane:
                problems.append(f"{label}: missing '{field}'.")

        status = lane.get("status")
        lane_type = lane.get("lane_type")
        authority = lane.get("authority")
        owners = lane.get("owner_repos")
        record = lane.get("activation_record")

        if status not in STATUSES:
            problems.append(f"{label}: status '{status}' is not one of {', '.join(sorted(STATUSES))}.")
        if lane_type not in LANE_TYPES:
            problems.append(f"{label}: lane_type '{lane_type}' is not one of {', '.join(sorted(LANE_TYPES))}.")
        if authority not in AUTHORITIES:
            problems.append(f"{label}: authority '{authority}' is not one of {', '.join(sorted(AUTHORITIES))}.")
        if not isinstance(owners, list) or not owners or not all(hqlib.is_text(o) for o in owners):
            problems.append(f"{label}: owner_repos must list at least one repo name.")
            owners = []
        elif registered is not None:
            for owner in owners:
                if owner not in registered:
                    problems.append(
                        f"{label}: owner repo '{owner}' is not registered in hq.yaml, so nobody can route this work."
                    )
        if "last_verified" in lane and hqlib.as_date(lane.get("last_verified")) is None:
            problems.append(f"{label}: last_verified must be a date written as YYYY-MM-DD.")
        if "next_action" in lane and not hqlib.is_text(lane.get("next_action")):
            problems.append(f"{label}: next_action must say what happens next.")

        if status == "active":
            if not hqlib.is_text(record):
                problems.append(
                    f"{label}: an active lane needs an activation_record (who approved it, when, and what scope)."
                )
            if lane_type == "implementation" and authority != "approved":
                problems.append(
                    f"{label}: active implementation lane does not have approved authority. "
                    "Either record the approval or move it back to queued."
                )
            if lane_type != "implementation" and authority == "approved":
                problems.append(
                    f"{label}: only implementation lanes carry approved authority; "
                    f"a {lane_type} lane should use planning_only."
                )
            if grants_permission(lane):
                for owner in owners:
                    active_build_lanes.setdefault(owner, []).append(str(lane_id))

        if status in NOT_STARTED:
            if authority == "approved":
                problems.append(
                    f"{label}: a {status} lane cannot carry approved authority. It would look like "
                    "permission. Use planning_only until the operator activates it."
                )
            if not hqlib.is_text(lane.get("activation_gate")):
                problems.append(
                    f"{label}: a {status} lane needs an activation_gate saying what must happen before work starts."
                )

        if status == "blocked":
            blocked_by = lane.get("blocked_by")
            if not isinstance(blocked_by, list) or not blocked_by:
                problems.append(f"{label}: a blocked lane must list what blocks it in blocked_by.")
            if authority == "approved":
                problems.append(f"{label}: a blocked lane cannot carry approved authority.")

        if status in CLOSED:
            if authority != "closed":
                problems.append(f"{label}: a {status} lane must have authority 'closed'.")
            if not hqlib.is_text(lane.get("completion_evidence")):
                problems.append(
                    f"{label}: a {status} lane needs completion_evidence (a link to the PR, task, or note)."
                )
        elif authority == "closed":
            problems.append(f"{label}: authority 'closed' is only for complete or cancelled lanes.")

    for repo, lane_ids in sorted(active_build_lanes.items()):
        if len(lane_ids) > 1:
            parallel_ok = all(
                isinstance(lane.get("parallel_approved"), bool) and lane["parallel_approved"]
                for lane in lanes
                if isinstance(lane, dict) and lane.get("id") in lane_ids
            )
            if not parallel_ok:
                problems.append(
                    f"repo '{repo}' has {len(lane_ids)} active implementation lanes ({', '.join(lane_ids)}). "
                    "Keep one per repo, or set parallel_approved: true on each after the operator agrees."
                )
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    parser.add_argument("--authorized", action="store_true", help="list the lanes that grant permission now")
    parser.add_argument("--repo", help="with --authorized, show only lanes for this repo")
    args = parser.parse_args(argv)
    try:
        root = hqlib.find_root(args.root)
        data = load_queue(root)
        registered = [repo.name for repo in hqlib.registered_repos(root)]
    except hqlib.HQError as exc:
        print(f"Work queue check could not run: {exc}")
        return 2

    problems = check_queue(data, registered)
    lanes = data.get("lanes") or []
    print(f"Work queue: {root / QUEUE_PATH}")
    print(f"Lanes: {len(lanes) if isinstance(lanes, list) else 0}")
    if problems:
        print(f"Problems: {len(problems)}")
        for problem in problems:
            print(f"- {problem}")
        print("Until these are fixed, treat no lane in this file as permission.")
        return 1
    print("Problems: 0")
    if args.authorized or args.repo:
        allowed = authorizing_lanes(data, args.repo)
        scope = f" for {args.repo}" if args.repo else ""
        if not allowed:
            print(f"No lane authorizes implementation{scope} right now. Only today's direct request can.")
        else:
            print(f"Lanes that authorize implementation{scope}:")
            for lane in allowed:
                print(f"- {lane['id']} ({', '.join(lane['owner_repos'])}): {' '.join(str(lane['next_action']).split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
