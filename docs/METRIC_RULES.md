# Metric rules (the single source of truth)

These rules are implemented once, in the dbt models, for BOTH data sources.

| Rule | Synthetic data | Online Retail II (real) |
|---|---|---|
| What is an order? | one row in `orders` (deduped by id) | one sales invoice with >= 1 real product line |
| Order status | given | none exists, so all such invoices are `completed` |
| Real product line | any item | 5-digit stock code AND price > 0 (excludes POST, M, BANK CHARGES, zero-price write-offs) |
| Shipping | `shipping_fee` column | lines with stock code POST or DOT. Never counted as revenue |
| Discounts | `discount` column | none in the data (0) |
| Refunds | `refunds` table, linked to an order | credit notes ("C..." invoices), NOT linked to an original order |
| Refund timing / limit | cannot exceed amount paid | subtracted on the day the credit note is issued |
| Duplicates | repeated order rows removed | exact duplicate lines removed |
| Currency | converted to GBP with `fx_rates` | already GBP |
| Staff/test customers | excluded | none identified |
| Missing customer id | n/a | order still counts as revenue, but is not counted as an active customer |

Net revenue = product revenue - discounts - linked refunds - unlinked returns.

## Assumptions to challenge
- Treating every real-data invoice as `completed` assumes the data only records
  finished sales.
- Credit notes are matched to a day, not to the invoice they reverse, because the
  data does not say which one that is.
- Stock-code and price rules are my reading of the dataset documentation. Check
  them against the real file (the prepare script prints summary stats).
