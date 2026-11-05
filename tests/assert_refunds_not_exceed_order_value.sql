-- The cap rule in int_order_totals must hold.
select order_id
from {{ ref('int_order_totals') }}
where refunded_gbp > gross_product_revenue_gbp + 0.01
  and status = 'completed'
