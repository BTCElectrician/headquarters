# Agent Rules for shop-api

The orders API for the example shop. shop-app is its main consumer.

## Start here

1. Read `STATUS.md`.
2. Check the branch and uncommitted changes before editing.

## How to build and check

| Task | Command |
| --- | --- |
| Tests | `python3 -m unittest discover -s tests` |

## Releases

- `main` does not deploy automatically. Releases are tagged by hand after a
  staging check, and tagging a release needs the operator's yes.

## Consumers

- shop-app calls `create_order`. Any change to its inputs or outputs must be
  checked against shop-app's checkout before it counts as done.

## Doors that stay closed without the operator's yes

- Releases, data migrations, spending, secrets, deletions, outside messages.
