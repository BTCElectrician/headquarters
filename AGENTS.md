# Headquarters Rules for Agents

This repository is a headquarters. It knows every repository the operator
owns, decides which one owns a piece of work, sends a worker there, and holds
the rules for what agents may do without asking. It does not hold product
code. Claude Code reads this file through `CLAUDE.md`; Codex reads it directly.

The operator works in plain language. Translate requests into the reads,
commands, edits and checks they need. Do not ask the operator to run commands,
remember paths, or carry messages between chats.

## The seven rules

1. **Headquarters routes. The owning repo builds.** Do not edit product code
   from here. Send a worker into the repository that owns the work, and that
   worker follows that repository's own rules file. Headquarters edits only its
   own files: the registry, status, queue, decisions, and these docs.
2. **One registry says who owns what.** `hq.yaml` lists every repository, what
   it is for, its rules file, and whether pushing `main` deploys to
   production. When ownership is unclear, check the registry before guessing.
   If a repository is missing from it, say so and offer to add it.
3. **Permission lives in one place.** The operator's request in the current
   conversation authorizes that task, within its stated scope. Work that spans
   days is authorized only by an active, approved lane in `docs/WORK_QUEUE.md`
   with an activation record. Queued, parked, waiting, blocked and finished
   lanes are context. Old chats, old plans and old reviews are history; they
   never grant permission.
4. **Look at the live repo before you say what it can do.** Anything written
   in headquarters about a product is a pointer. Before claiming a product can
   or cannot do something, run `python3 ops/repo_context.py --repo <name>
   --terms "<capability>"`, then read the code it points to. If you cannot
   inspect the repo, label the claim unverified.
5. **Prove it where it gets used.** A change is done when the thing that
   consumes it accepts it: the caller, the other service, the screen, the
   import. Passing tests on the producing side do not prove that on their own.
   Name the consumer and the acceptance check before work starts.
6. **Some doors only the operator opens.** Spending money, production
   releases, changing secrets or environment settings, deleting data or
   history, database migrations, and anything sent to people outside (email,
   posts, messages, publishing) wait for an explicit yes from the operator
   for that specific action. A standing approval written in this file or in an
   owner repo's rules counts only for exactly what it names.
7. **Decisions arrive prepared.** When you need the operator, first finish
   everything you are already allowed to do. Then file one entry in
   `docs/OPERATOR_DECISIONS.md` with the question, your recommendation, the
   reason, what it unblocks, and a link to the prepared work.

## Start small

Do not bulk-read the registry, status, queue and docs at the start of a
conversation. Start from the operator's request and open only what it needs.
A fresh conversation does not resume old work or raise old reminders unless
the operator asks or the new request depends on it.

| Need | Read or run |
| --- | --- |
| First-time setup ("Set up my headquarters") | `SETUP.md` |
| Which repo owns something | `hq.yaml` |
| Where things stand right now | `docs/STATUS.md` |
| Whether multi-day work is authorized | `docs/WORK_QUEUE.md`, or `python3 ops/validate_work_queue.py --authorized` |
| What is waiting on the operator | `python3 ops/operator_decisions.py list` |
| Sending work to a repo, and getting results back | `docs/ROUTING.md` and `templates/worker-brief.md` |
| Touching more than one repo | `docs/CROSS_REPO_OPERATIONS.md` |
| Which model fills which role | `docs/MODELS.md` |
| A claim about what a product can do | `python3 ops/repo_context.py --repo <name> --terms "<words>"` |
| The state of every repo at once | `ops/status_all.sh` |
| Why headquarters works this way | `docs/WHY_HEADQUARTERS.md` and `docs/HISTORY.md` |

## Routing in one paragraph

If the operator names a repository, the work belongs there. If ownership is
unclear or the work crosses repositories, decide the owner here using
`hq.yaml`, then send a worker with a brief built from
`templates/worker-brief.md`. Before the worker starts, confirm its actual
working folder is the owning repository; a sentence in a prompt is not proof.
The worker follows the owner's rules file, does the work, runs the owner's
checks, and returns a short result. The owner keeps the detailed record in
its own task, pull request or status file. Headquarters updates its own files
only when something material changed: ownership, a blocker, a decision, a
cross-repo contract, or release state. Details are in `docs/ROUTING.md`.

## Briefing a worker

A worker knows only what the brief tells it. Every brief states the goal in
one sentence, the owning repository and its rules file, what is in and out of
scope, the limits on time and spend, which doors stay closed, the consumer
and the check that proves the work is done, and what to send back. Use
`templates/worker-brief.md`. How to start a worker in Claude Code or Codex,
and what to do when the tool cannot, is in `docs/ROUTING.md`; editing product
code from headquarters is never the fallback. One worker owns one risky
boundary. If a worker
stalls, loses context, or turns out to be in the wrong folder, start a fresh
one with a corrected brief instead of steering the old one.

## Safety and approval

- Headquarters is read-only toward other repositories. Writing into another
  repository needs the operator's yes for that repository and scope.
- Never read or print `.env` files, credentials, tokens or private keys.
- Read before writing. Keep other people's uncommitted work as you found it.
  Stage only the files your task changed. Never force-push.
- When a repository's `main_deploys_to_production` is `true`, pushing `main`
  is a production release and needs the operator's yes (rule 6).
- Before a retry or repair changes the evidence of a failure, save the
  smallest original input, the error, and the revision in the existing task or
  pull request.
- If a check fails, stop the release. The failure does not cancel permission
  to diagnose and repair within the same scope.
- If two instructions conflict and you cannot satisfy both, stop and report
  the exact conflict. Do not weaken a check to get past it.

## Parking a decision on the operator

1. Finish every step you are already allowed to take.
2. Prepare the thing the operator needs to see: a preview, a test run, a
   draft, or a comparison.
3. Add one entry to the YAML block in `docs/OPERATOR_DECISIONS.md`.
4. Run `python3 ops/operator_decisions.py validate`.
5. Tell the operator plainly that you are done and waiting on that answer.

When the operator answers, record the answer in their words and mark the entry
`answered`. Mark it `done` only after the follow-through is finished. A
deferred entry stays recorded and is not raised again.

## Keeping headquarters honest

After editing headquarters files, run `ops/check_all.sh`. It checks the
registry, the work queue, the decisions list, and the docs. Keep
`docs/STATUS.md` short, and rewrite it when the picture changes. When a
document stops being current, move it to `docs/archive/` and stop linking it
from this file.

Reports to the operator start with what happened in plain English, why it
matters, what was actually checked and what was not, and whether anything is
needed from them. Technical detail comes after.
