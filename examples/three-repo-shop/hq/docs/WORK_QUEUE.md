<!-- reviewed: {{TODAY}} | review every: 7 days -->
# Work Queue

Example data for the made-up three-repo shop. The rules for this file are in
the starter's own `docs/WORK_QUEUE.md`.

<!-- work-queue:start -->
```yaml
schema_version: work_queue.v1
lanes:
  - id: order-lookup-by-email
    status: active
    lane_type: implementation
    owner_repos: [shop-api]
    authority: approved
    activation_record: >
      Operator approved on {{TODAY}} in chat: add order lookup by email to
      shop-api, with tests. No release without a separate yes.
    next_action: "Worker adds the lookup and a test that fails without it."
    last_verified: {{TODAY}}
  - id: refund-button
    status: queued
    lane_type: implementation
    owner_repos: [shop-app, shop-api]
    authority: planning_only
    activation_gate: "Operator answers refund-button-scope, then approves the plan."
    next_action: "Draft the plan once the scope decision is answered."
    last_verified: {{TODAY}}
  - id: help-site-search
    status: complete
    lane_type: implementation
    owner_repos: [shop-docs]
    authority: closed
    completion_evidence: "shop-docs commit 'Add search page' (example)."
    next_action: "None."
    last_verified: {{TODAY}}
```
<!-- work-queue:end -->
