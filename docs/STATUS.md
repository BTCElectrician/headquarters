<!-- reviewed: 2026-11-12 | review every: as needed -->
# Headquarters Status

This file says where things stand right now. It is a snapshot, not a diary:
rewrite it when the picture changes, and keep history in git.

## Right now

Headquarters is not set up yet. No repositories are registered in `hq.yaml`.
To set it up, open Claude Code or Codex in this folder and say "Set up my
headquarters." The agent follows `SETUP.md` and rewrites this file when it is
done.

## What this file holds after setup

- **Repositories:** how many are registered, and any that are missing or lack
  a rules file.
- **Active work:** the lanes in `docs/WORK_QUEUE.md` that currently grant
  permission, one line each.
- **Waiting on you:** the count of open entries in
  `docs/OPERATOR_DECISIONS.md`, with the top one named.
- **Known limits:** anything set up but not yet checked, said plainly.
- **Next step:** the single most useful next action.

After setup, change the review line at the top of this file to
`review every: 7 days` so the docs check flags it when it goes stale.
