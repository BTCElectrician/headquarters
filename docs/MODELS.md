<!-- reviewed: 2026-11-12 | review every: as needed -->
# Models: Which Model Fills Which Role

Rules in this headquarters name roles, never specific models. This page is the
only place that says which model currently fills each role, so switching to a
newer model means editing one table and nothing else.

## Roles

| Role | What it does | Model | Effort or setting |
| --- | --- | --- | --- |
| Lead | Talks with the operator, plans, routes work, makes judgment calls, does final review. | _fill in_ | _fill in_ |
| Worker | Does one bounded job inside an owning repository: build, debug, test, research. | _fill in_ | _fill in_ |
| Reviewer | Reads a finished change fresh, without the builder's context, and reports problems. | _fill in_ | _fill in_ |
| Escalation reviewer (optional) | A slower, more expensive second opinion for a hard, clearly framed question. | _fill in_ | _fill in_ |

Example of a filled-in row, to show the shape (pick your own):

| Role | What it does | Model | Effort or setting |
| --- | --- | --- | --- |
| Worker | Does one bounded job inside an owning repository. | the mid-size model from your coding tool | medium |

## How to use the roles

- Give most bounded work to the worker role. Keep the lead for planning,
  decisions and final review.
- Use the reviewer when an independent read is worth the cost: a release, a
  data change, a security-sensitive change, or a result the builder cannot
  judge on its own. Give the reviewer the actual code and evidence, not the
  builder's conclusion.
- One fresh review and one round of fixes is the default. Another round needs
  the operator's agreement.
- Use the escalation reviewer only for a frozen, difficult question with a
  clear way to judge the answer, and only within an approved spend limit.

## Spend

| Setting | Value |
| --- | --- |
| Default spend limit per worker task | _fill in, for example "no paid API calls without asking"_ |
| Who may approve more | the operator |
