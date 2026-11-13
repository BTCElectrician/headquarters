# Agent Rules for shop-app

The web storefront for the example shop. It calls shop-api to create orders.

## Start here

1. Read `STATUS.md`.
2. Check the branch and uncommitted changes before editing.

## How to build and check

| Task | Command |
| --- | --- |
| Tests | `node --test` |

## Releases

- Merging to `main` publishes the storefront to production. A merge to main
  is a release and needs the operator's yes.

## Doors that stay closed without the operator's yes

- Production releases, spending, secrets, deletions, and outside messages.
