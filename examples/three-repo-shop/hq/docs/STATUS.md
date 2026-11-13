<!-- reviewed: {{TODAY}} | review every: 7 days -->
# Headquarters Status

Example data for the made-up three-repo shop.

## Right now

Three repositories are registered: the storefront app, the orders API, and
the help site. The help site has no rules file yet, so workers there have no
local rules; the operator has not decided whether to add one.

## Active work

- `order-lookup-by-email` in shop-api: add a way to look up orders by email.
  Approved; a worker is building it.

## Waiting on you

One open decision: `refund-button-scope`, whether the first refund button
should allow partial refunds.

## Known limits

- shop-docs releases from main, and nothing checks its links yet.

## Next step

Answer `refund-button-scope` so the refund lane can be planned.
