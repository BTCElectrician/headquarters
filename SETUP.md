# Setting Up a Headquarters

This is the script an agent follows when the operator says "Set up my
headquarters." The operator should not need to type a command. Ask the
questions below in plain words, do the work, and report back.

Ground rules for the whole setup:

- Inside this headquarters folder you may create and edit files.
- Toward every other repository you are read-only. Do not create, edit,
  commit or push anything in another repository unless the operator says yes
  to that specific repository and file.
- Never open `.env` files, credentials, tokens or private keys while reading
  repositories.
- Needs: `git`, `bash`, and Python 3.9 or newer. No packages to install.

## Step 1: Ask where the repositories live

Ask: "Which folder holds your repositories?" Most people keep them side by
side in one folder, such as a code or projects folder. If they live in
several places, ask for each one.

If this headquarters folder sits in the same folder as the repositories, keep
`repos_root: ".."` in `hq.yaml`. Otherwise set `repos_root` to that folder
(an absolute path or a path starting with `~`).

## Step 2: Find the git repositories

Run the read-only discovery helper on each folder. Give it the folder that
holds the repositories, not a repository itself. When this headquarters sits
beside the repositories, that folder is `..`:

```bash
python3 ops/hqlib.py discover ..
python3 ops/hqlib.py discover <folder>
```

It lists every git repository directly inside the folder and drafts a
registry entry for each. It reads only README, AGENTS.md and STATUS.md
locations and a few deploy files. It writes nothing.

Show the operator the list of repository names and ask which ones this
headquarters should know about. Leave out anything they say is archived,
experimental or private to someone else. Do not register this headquarters
folder itself.

## Step 3: Read each chosen repository lightly

For each chosen repository, read only enough to describe it: the README
opening, the `AGENTS.md` or other rules file if one exists, and the status
file if one exists. Check the current branch and whether there are uncommitted
changes. Do not run its builds or tests, and do not read source code beyond
what you need to write one sentence about its purpose.

## Step 4: Propose the registry entries

For each repository, propose:

- `purpose`: one plain sentence saying what it is for. Improve the drafted
  sentence from the README if it is vague.
- `rules_file`: `"AGENTS.md"` if it exists, otherwise `null`.
- `status_file`: the current-state file, if there is one.
- `main_deploys_to_production`: the discovery helper leaves this as
  `ask-the-operator` on purpose. Ask the operator for each repository: "When
  something is pushed or merged to main in this repository, does it go live
  to production automatically?" Mention any deploy hints the helper found.
  Record `true` or `false`. Never guess this one.

Ask which repositories depend on another one (for example an app that calls
an API) and record that as `uses` on the one that depends.

Offer optional `groups` if the operator describes repositories that belong
together (for example an app and its API).

Show the operator the proposed entries in a short table, apply their
corrections, then write them into `hq.yaml`.

## Step 5: Offer rules files where they are missing

For each repository whose `rules_file` is `null`, tell the operator that
workers there will have no local rules, and offer to add one based on
`templates/owner-repo/AGENTS.md`. Ask once per repository.

One yes covers one file. A yes to the rules file does not cover adding a
`STATUS.md`. If the repository has no status file, ask about
`templates/owner-repo/STATUS.md` as a separate question.

Only on a clear yes:

1. Fill the template from what you read (build and test commands, release
   rule) and show the operator the filled-in file.
2. Check whether the repository has uncommitted changes (`git status`).
   - If it is clean, note the branch it is on, create a new branch, write
     the file, and commit it on that branch. Then switch the repository back
     to the branch it was on.
   - If it has uncommitted changes, do not switch branches in its working
     folder at all. Create a separate worktree on a new branch
     (`git worktree add <new folder> -b <branch>`), write and commit the file
     there, and leave the original working folder untouched. Tell the
     operator where the worktree is.
3. Do not commit to `main`, merge, or push unless the operator asks.
4. Keep `rules_file: null` in `hq.yaml` for now. The file exists only on the
   new branch, so pointing the registry at it would be true only while that
   branch is checked out. Change `rules_file` to `"AGENTS.md"` after the
   operator merges the branch.
5. Record the pending branch in `docs/STATUS.md`, for example: "shop-docs:
   rules file waiting on branch `add-agent-rules`; change `rules_file` in
   hq.yaml after it is merged."
6. Tell the operator the branch name and that it is waiting on their merge.

If they decline, leave `rules_file: null`. The registry check will keep a
note about it either way.

## Step 6: Fill in the rest of headquarters

- `docs/MODELS.md`: ask which models the operator uses for the lead, worker
  and reviewer roles, and fill the table. If they have no preference, leave
  the blanks as they are and say so. The checks still pass with the blanks
  left in.
- `docs/WORK_QUEUE.md` and `docs/OPERATOR_DECISIONS.md`: leave empty unless
  the operator names multi-day work or an open decision. If they do, add it
  following the rules in each file.
- `docs/STATUS.md`: rewrite it with the current picture: how many
  repositories are registered, any missing rules or status files, active
  work, anything waiting on the operator, known limits, and the next step.
  Change its first line to
  `<!-- reviewed: <today> | review every: 7 days -->`, where `<today>` is the
  system date written as YYYY-MM-DD (the output of `date +%F`).

## Step 7: Run the checks

```bash
ops/check_all.sh
ops/status_all.sh
```

`check_all.sh` must end with "All checks passed." If a check fails, fix the
headquarters file it names and run it again. If a failure can only be fixed in
another repository (for example a missing rules file the operator declined),
report it instead of working around it. `status_all.sh` shows the branch and
state of every registered repository; include anything surprising in your
report.

Commit the headquarters changes in this repository with a message such as
`chore: set up headquarters registry`. Do not push unless the operator asks.

## Step 8: Tell the operator what was set up

Report in plain English, in this order:

1. What headquarters now knows: the repositories registered, one line each,
   and which ones deploy to production from `main`.
2. What you added to other repositories, if anything, and on which branch.
3. What you did not do or could not check, said plainly.
4. Anything that waits on them, with your recommendation.
5. How to use it from now on, for example: "Ask me from this folder for
   anything that spans your repositories. I will route the work to the repo
   that owns it."
