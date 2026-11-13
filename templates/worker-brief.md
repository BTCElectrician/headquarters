# Worker Brief

Headquarters fills in this brief and hands it to a worker. The worker knows
only what the brief says, so write every line so it stands on its own.

## Goal

<One sentence: the outcome, as the operator would describe it.>

## Where

- Owning repository: <name from hq.yaml>
- Rules to follow there: <rules file, usually AGENTS.md>
- Confirm before editing: your working folder is <path>, or a worktree of it.

## Permission

- Authorized by: <today's request from the operator, quoted briefly, or the
  active work-queue lane id>
- In scope: <what the worker may change>
- Out of scope: <what the worker must not touch>
- Doors that stay closed: <for example production release, migrations,
  secrets, spending, outside messages>

## Limits

- Time: <a wall-clock limit>
- Spend: <a cap on paid calls, or "none">
- Stop and report if either limit is reached. Do not extend it yourself.

## Done means

- Consumer: <the caller, screen, service or import that must accept the change>
- Acceptance check: <the exact command or step that proves it>
- Owner checks: <the repository's test and lint commands>

## Starting evidence

- <Links or paths to the failing case, error, saved input, or prior result.>

## Send back

A short report in plain English, then the details:

1. What changed, and where (branch, pull request, commit).
2. What was checked, with the command and result.
3. What was not checked, and why.
4. Anything now waiting on the operator, prepared as a decision.
5. Any temporary copies, worktrees or processes left behind (there should be
   none).
