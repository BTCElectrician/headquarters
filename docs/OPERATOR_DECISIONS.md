<!-- reviewed: 2026-11-12 | review every: as needed -->
# Operator Decisions

This is the one list of questions waiting on the operator. Each entry is
prepared before it is filed: the agent has finished everything it was allowed
to do, built whatever the operator needs to look at, and written down its
recommendation. Answering an entry should take a few minutes.

To see what is waiting, most urgent first:

```bash
python3 ops/operator_decisions.py list
```

## Rules for agents

- File an entry only after the preparation is done. An open entry must link
  to the prepared work (a preview, a test result, a draft, a comparison).
- Write the question so it can be answered without opening anything else.
- Every entry carries a recommendation and the reason for it. A bare list of
  options is not a prepared decision.
- One question per entry. If there are two decisions, file two entries.
- A setting that simply stays off until the operator says otherwise is not a
  decision. Keep it in its owner's record until there is a real question.
- When the operator answers, record the answer in their own words, set
  `status: answered`, and fill `answered_on`. Set `status: done` and
  `closed_on` only after the follow-through is finished.
- A deferred entry stays recorded with its reason and is not raised again.
- Update `last_checked` whenever you confirm an entry is still waiting. The
  list marks entries not rechecked for 14 days.
- Set `due` only for a real deadline.

Ranking: entries with a `due` date come first (soonest first), then by impact
(`outside`, `money`, `unblock`, `internal`), then the oldest.

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | always | Short unique name, lowercase with hyphens. |
| `status` | always | `open`, `answered`, `done`, `deferred`, or `withdrawn`. |
| `question` | always | The exact question, answerable on its own. |
| `recommendation` | always | What the agent recommends. |
| `why` | always | The reason for the recommendation. |
| `unblocks` | always | What can proceed once this is answered. |
| `prepared` | when open | Link or path to the prepared work. |
| `owner` | always | Who carries the follow-through after the answer. |
| `minutes` | always | Honest estimate of the operator's time, a whole number. |
| `impact` | always | `outside` (affects people outside), `money`, `unblock`, or `internal`. |
| `opened`, `last_checked` | always | Dates, YYYY-MM-DD. |
| `due` | no | A real deadline, YYYY-MM-DD. |
| `answer`, `answered_on` | when answered | The operator's words and the date. |
| `deferred_reason`, `deferred_on` | when deferred | Why it was set aside, and when. |
| `closed_on` | when done or withdrawn | Date the entry was closed. |

## Example entry

This example is outside the machine-readable block, so it is not checked.

```yaml
  - id: pick-error-tracker
    status: open
    question: >
      Should storefront-app send errors to the hosted error tracker on its
      free plan, starting this week?
    recommendation: Yes, on the free plan.
    why: >
      The trial run caught two real crashes in a day, and the free plan covers
      our volume with room to spare.
    unblocks: Alerting for the checkout page.
    prepared: "storefront-app pull request 42 (draft, tests passing)"
    owner: storefront-app worker
    minutes: 5
    impact: unblock
    opened: 2026-11-12
    last_checked: 2026-11-12
```

## Decisions

Edit only the YAML between the marker lines. Keep the markers and the single
fenced block intact. When nothing is waiting, leave `decisions: []`.

<!-- operator-decisions:start -->
```yaml
schema_version: operator_decisions.v1
decisions: []
```
<!-- operator-decisions:end -->
