<!-- reviewed: {{TODAY}} | review every: 7 days -->
# Operator Decisions

Example data for the made-up three-repo shop. The rules for this file are in
the starter's own `docs/OPERATOR_DECISIONS.md`.

<!-- operator-decisions:start -->
```yaml
schema_version: operator_decisions.v1
decisions:
  - id: refund-button-scope
    status: open
    question: >
      Should the first version of the refund button allow partial refunds, or
      only full refunds?
    recommendation: Full refunds only for the first version.
    why: >
      Full refunds need no change to how the API stores order totals, so the
      first version can ship in days instead of weeks. Partial refunds can
      follow once the full-refund flow is in use.
    unblocks: Planning and activating the refund-button lane.
    prepared: "shop-api/docs/plans/refunds.md (both options written out)"
    owner: HQ lead
    minutes: 5
    impact: outside
    opened: {{TODAY}}
    last_checked: {{TODAY}}
  - id: help-site-rules-file
    status: deferred
    question: Should shop-docs get an AGENTS.md rules file?
    recommendation: Yes, from the owner-repo template.
    why: Workers there currently have no local rules.
    unblocks: Safer edits to the help site.
    owner: HQ lead
    minutes: 3
    impact: internal
    opened: {{TODAY}}
    last_checked: {{TODAY}}
    deferred_reason: "The operator wants to wait until the help site changes more often."
    deferred_on: {{TODAY}}
```
<!-- operator-decisions:end -->
