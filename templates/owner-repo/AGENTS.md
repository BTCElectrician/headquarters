# Agent Rules for <repo name>

<One or two sentences: what this repository is and who uses it.>

This repository is registered with a headquarters. Headquarters decides which
repository owns a piece of work and sends a worker here. Once you are here,
these rules apply, and they win over general habits.

## Start here

1. Read `STATUS.md` for where things stand right now.
2. Check the branch, the latest commit, and uncommitted changes before you
   edit anything. Someone else may be working here; keep their changes as you
   found them.
3. Open only the files your task needs.

## How to build and check

| Task | Command |
| --- | --- |
| Install | `<install command>` |
| Run locally | `<run command>` |
| Tests | `<test command>` |
| Lint or type check | `<lint command, or "none">` |

Run the tests before saying a change works. If a test fails, report it; do not
weaken the test to make it pass.

## Releases

- Pushing or merging to `main` <does / does not> deploy to production.
- <If it does: a push to main is a release and needs the operator's yes,
  followed by a check that the deployed version is the one you meant and is
  healthy.>

## Doors that stay closed without the operator's yes

- Spending money, production releases, and database migrations.
- Changing secrets or environment settings.
- Deleting data, branches or history. Never force-push.
- Sending anything to people outside (email, posts, messages, publishing).

Never read or print `.env` files, credentials or tokens.

## When you finish

Update `STATUS.md` only if the current state or the next step changed. Keep
detailed evidence in the pull request or task. Report back in plain English:
what changed, what you checked, what you did not check, and anything that now
waits on the operator.
