<!-- reviewed: 2026-11-12 | review every: as needed -->
# Cross-Repo Operations

These rules apply whenever work touches more than one repository, or when an
agent in headquarters is about to do anything inside another repository. Each
one exists because skipping it causes a specific, expensive kind of mistake.

## Before touching another repository

1. **Know the owner.** Look the repository up in `hq.yaml` and read its rules
   file. Its rules win over general habits.
2. **Confirm the folder.** Check the actual working folder of the agent that
   will make the change. Wrong-folder edits are the most common cross-repo
   accident, and they are easy to miss because the agent sounds confident.
3. **Check what is already there.** Look at the branch, the latest commit, and
   uncommitted changes. Another agent or person may be working there. Several
   dirty repositories at once is normal. Treat it as a reason to be careful,
   and leave those changes alone.
4. **Isolate your work.** Use a separate branch or a separate worktree so you
   never build on, stage, or reset someone else's unfinished changes. When
   the owning repository has uncommitted changes, do not switch branches in
   its working folder: create a separate worktree from the last committed
   state and leave those changes alone.
5. **Have permission for that repository.** Writing into another repository
   needs the operator's yes for that repository and that scope.

## While working

- Read before writing.
- Stage only the files your task changed. Check the exact diff before each
  commit.
- Never force-push. Never rewrite shared history.
- Never read, print or copy secrets, `.env` files, tokens or credentials.
- Prefer small, incremental data operations. Do not rebuild an index, re-run
  a full import, or bulk-rewrite records unless the operator approved that
  exact operation.
- Keep one active build lane per repository unless the operator approved
  parallel lanes and each lane names the files it owns.
- When a step fails, save the smallest original input, the error, and the
  revision before trying again. A retry that overwrites the evidence makes the
  failure harder to understand.

## Releases

- `main_deploys_to_production: true` in `hq.yaml` means pushing or merging to
  `main` is a production release. That needs the operator's yes, then a check
  that the deployed revision is the one you meant and that it is healthy.
- A failed check stops a release. Report it; do not route around it.
- A passing test suite, a merged pull request or a deployed image is not the
  same as the user-facing result working. Check the result where it is used.

## Producer and consumer

When repository A produces something repository B consumes:

1. Name the consumer and its acceptance check before work starts.
2. Run that check early on a real saved input, with irreversible effects
   switched off (dry run, staging, a copy).
3. Count the work done only when the consumer accepts the output. A
   producer's own tests and matching outputs do not prove it.

If a safe check of the real boundary is not possible, say the boundary is
unverified instead of claiming it works.

## Cleaning up

Remove temporary clones, worktrees and processes your task created once its
work is saved. Leave alone anything another task created, even if it looks
abandoned. If you are unsure who owns it, report it instead of deleting it.
