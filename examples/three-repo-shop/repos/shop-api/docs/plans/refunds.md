# Refunds plan (not built)

Two options for the first refund button:

1. Full refund only. The API marks the whole order refunded. No change to how
   order totals are stored.
2. Partial refund. The API records refunded line items, which needs a change
   to how totals are stored and a migration.

Nothing in the code handles refunds yet.
