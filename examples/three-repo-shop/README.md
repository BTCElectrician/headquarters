# Example: a Three-Repo Shop

A made-up business with three repositories, so you can run the whole
headquarters loop without touching your own code:

- **shop-app**: the web storefront. Pushing `main` deploys it to production.
- **shop-api**: the orders API the storefront calls. Releases are manual.
- **shop-docs**: the public help site. It has no rules file yet.

The folders under `repos/` and `hq/` are plain files, not git repositories,
so this starter does not contain nested repos. The script below copies them to
a folder you choose and turns each one into a real git repository.

## Build it

```bash
python3 examples/three-repo-shop/materialize.py /tmp/shop-example
cd /tmp/shop-example/headquarters
```

You get `repos/shop-app`, `repos/shop-api`, `repos/shop-docs`, and a
`headquarters/` folder: a copy of this starter with the example registry,
status, work queue and decisions filled in.

## Things to try

| Try | What you should see |
| --- | --- |
| `ops/status_all.sh` | All three repos, with shop-app marked dirty (someone is mid-edit). |
| `ops/check_all.sh` | Every check passes, with a note that shop-docs has no rules file. |
| `python3 ops/validate_work_queue.py --authorized` | Only `order-lookup-by-email` grants permission. The queued refund lane does not. |
| `python3 ops/operator_decisions.py list` | One open decision, with a recommendation and a link to the prepared plan. |
| `python3 ops/repo_context.py --repo shop-api --terms "create order"` | Matches in code and tests, and the release rule for shop-api. |
| `python3 ops/repo_context.py --repo shop-api --terms "refund"` | Matches only in docs: refunds are planned, not built. |

Then open Claude Code or Codex in the `headquarters/` folder and ask for
something that needs routing, such as "Add a free-shipping banner to the
storefront" or "Can customers get refunds yet?" Watch whether it picks the
right repo, checks permission, and looks at the live code before answering.

## Watch the checks catch problems

```bash
python3 examples/three-repo-shop/materialize.py /tmp/shop-broken --broken
cd /tmp/shop-broken/headquarters
ops/check_all.sh
```

This version plants five problems: a registered repo that does not exist, a
queued lane that claims approval, an open decision with no recommendation, a
doc nothing links to, and a status file past its review date. Each check
names the problem in plain words and exits with an error.
