<!-- reviewed: 2026-11-12 | review every: as needed -->
# Work Queue

This is the one record of work that is authorized across days. A request the
operator makes in the current conversation is authorized on its own and does
not need an entry here. An entry is needed when work must outlive the
conversation: a multi-day build, something a later agent will pick up, or
work several agents share.

## The permission rule

A lane authorizes building only when all four of these hold:

1. `status` is `active`,
2. `lane_type` is `implementation`,
3. `authority` is `approved`,
4. `activation_record` says who approved it, when, and for what scope.

Everything else is context. A queued lane, a parked idea, a lane waiting on
an answer, a blocked lane, and a finished lane do not grant permission, even
if they describe the work in detail. Status (where it is), authority (whether
anyone may build it) and the activation record (proof of the yes) are kept in
separate fields so one cannot be mistaken for another.

To see which lanes grant permission right now:

```bash
python3 ops/validate_work_queue.py --authorized
```

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Short unique name, lowercase with hyphens. |
| `status` | yes | `active`, `queued`, `parked`, `waiting`, `blocked`, `complete`, or `cancelled`. |
| `lane_type` | yes | `implementation` (changes code), `coordination`, or `research`. |
| `owner_repos` | yes | Repositories that own the work, as named in `hq.yaml`. |
| `authority` | yes | `approved`, `planning_only`, `none`, or `closed`. |
| `next_action` | yes | The next concrete step. |
| `last_verified` | yes | Date someone last confirmed this entry is true (YYYY-MM-DD). |
| `activation_record` | when active | Who said yes, when, and the scope and limits they gave. |
| `activation_gate` | when queued, parked or waiting | What must happen before work can start. |
| `blocked_by` | when blocked | A list of what is in the way. |
| `completion_evidence` | when complete or cancelled | Link to the pull request, task or note that closes it. |
| `plan` | no | Path or link to the one current plan for this lane. |
| `parallel_approved` | no | `true` only when the operator agreed to two active build lanes in one repository. |

The check (`python3 ops/validate_work_queue.py`) fails when:

- an active lane has no activation record,
- an active implementation lane lacks approved authority,
- a queued, parked, waiting or blocked lane carries approved authority,
- a finished lane is not closed or has no completion evidence,
- a lane names a repository that is not in `hq.yaml`,
- one repository has two active build lanes without `parallel_approved`.

## Example lane

This example is outside the machine-readable block, so it is not checked and
grants nothing.

```yaml
  - id: checkout-retry
    status: active
    lane_type: implementation
    owner_repos: [storefront-api]
    authority: approved
    activation_record: >
      Operator approved on 2026-11-12 in chat: add retry to the payment call,
      storefront-api only, no production release without a separate yes.
    plan: "storefront-api/docs/plans/checkout-retry.md"
    next_action: "Worker adds retry with a test that fails without it."
    last_verified: 2026-11-12
```

## Lanes

Edit only the YAML between the marker lines. Keep the markers and the single
fenced block intact. When there are no lanes, leave `lanes: []`.

<!-- work-queue:start -->
```yaml
schema_version: work_queue.v1
lanes: []
```
<!-- work-queue:end -->
