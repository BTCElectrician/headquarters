<!-- reviewed: 2026-11-12 | review every: as needed -->
# Routing: From Headquarters to the Owning Repo and Back

Headquarters knows, routes and records. The repository that owns the work
does the work. This page describes how a request travels from the operator to
the right repository and how the result comes back.

## The shortcut

If the operator already names the repository, the work starts there. If the
owner is unclear, or the work touches several repositories, headquarters
decides the owner first. Known repo: go there. Unknown owner: route from here.

## The loop

1. **Find the owner.** Read `hq.yaml`. Match the request to a repository's
   `purpose`. If two repositories could own it, the one whose code changes is
   the owner; the others are consumers. If none fits, ask the operator one
   short question rather than guessing.
2. **Check permission.** A direct request in the current conversation is
   permission for that task. For work picked up from an earlier session, the
   only permission is an active, approved lane in `docs/WORK_QUEUE.md`. Run
   `python3 ops/validate_work_queue.py --authorized --repo <name>` if unsure.
3. **Get live facts.** Before describing what the owner can do today, run
   `python3 ops/repo_context.py --repo <name> --terms "<words>"`, then read the
   code it points to. Headquarters notes about a product may be weeks old.
4. **Brief a worker.** Fill in `templates/worker-brief.md`. Name the consumer
   that must accept the change and the check that proves it. Name the doors
   that stay closed.
5. **Confirm the workspace.** Before the worker edits anything, confirm its
   actual working folder is the owning repository (or an isolated worktree of
   it). The tool's recorded folder is the proof; text in a prompt is not.
6. **The worker builds under the owner's rules.** It reads the owner's rules
   file and status file, makes the change, runs the owner's checks, and
   exercises the consumer. Detailed evidence goes in the owner's pull request
   or task.
7. **Return a short result.** The worker sends back what changed, where the
   evidence lives, what was checked and what was not, and any open door. The
   agent that took the operator's request stays responsible for the outcome
   until the consumer accepts the change and the operator has a plain answer.
8. **Update headquarters only when it matters.** Change `docs/STATUS.md`, the
   work queue, or the decisions list only when ownership, a blocker, a
   decision, a cross-repo contract, or release state changed. Routine work
   needs no headquarters entry.

## Launching a worker

A worker is a separate agent whose working folder is the owning repository.
How to start one depends on the tool:

- **Claude Code:** start a subagent whose working folder is the owning
  repository, or open a new session in that repository.
- **Codex:** open a new thread in the owning repository.
- **If the tool cannot start a worker:** give the operator the filled-in
  brief from `templates/worker-brief.md` and ask them to open their agent in
  that repository and paste it in.

Editing product code from headquarters is never the fallback. If no worker
can be started, the work waits for the operator to open one.

## When the owning repository has uncommitted changes

Someone may be mid-edit there. The worker does not build on, stage, stash or
reset those changes. It works in a separate worktree created from the last
committed state (`git worktree add <new folder> -b <branch>`), and leaves the
original working folder exactly as it found it.

## What headquarters may do

- Maintain `hq.yaml`, `docs/STATUS.md`, `docs/WORK_QUEUE.md`,
  `docs/OPERATOR_DECISIONS.md` and the other docs here.
- Read other repositories to route work, answer questions, or check status.
  Reading is always allowed; writing is not.
- Prepare worker briefs and review what workers return.
- Record outcomes that change the portfolio picture.

## What headquarters does not do

- Edit, build, test, release or migrate anything inside another repository
  from the headquarters conversation itself. A worker in that repository does
  that, under that repository's rules.
- Copy a product's documentation into headquarters. Each repository documents
  itself. A copy goes stale and then misleads.
- Keep a separate completion record for every small task. The owner's pull
  request or task is the record.
- Treat an old plan, an old review, or an earlier chat as permission.

## When two repositories are involved

When one repository produces something another consumes (an API and the app
that calls it, a data export and the import that reads it), plan for the
consumer from the start. Name the consumer, find a real saved input, and run
the consumer's actual acceptance step on the new output early, with any
irreversible effect switched off. Matching outputs on the producing side do
not prove the consumer accepts them. Safety rules for this kind of work are
in `docs/CROSS_REPO_OPERATIONS.md`.

## Worker lifecycle

One worker owns one risky boundary and has its own limits on time and spend.
A worker already handling a task may continue from diagnosis to repair to
verification inside the same scope. Start a fresh worker when the current one
has lost context, is in the wrong folder, has stalled, or when a reviewer
needs to be independent of the builder. When a worker finishes, it removes
any temporary copy or worktree it created and reports what it left behind.
