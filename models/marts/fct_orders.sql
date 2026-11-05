-- GOVERNED DEFINITION OF A "REVENUE ORDER"  (same for every source system)
--   * status = 'completed'
--   * customer is not internal (orders with NO customer id still count:
--     the money was real, we just cannot attribute it to a person)
--   * deduplicated upstream
--   * net revenue = items - discount - linked refunds, in GBP, excludes shipping
select
    t.order_id,
    t.customer_id,
    (t.customer_id is not null)               as has_customer,
    t.ordered_at,
    t.order_date,
    t.currency,
    t.gross_product_revenue_gbp,
    t.refunded_gbp,
    t.gross_product_revenue_gbp - t.refunded_gbp as net_revenue_gbp,
    t.shipping_gbp
from {{ ref('int_order_totals') }} t
left join {{ ref('dim_customers') }} c using (customer_id)
where t.status = 'completed'
  and not coalesce(c.is_internal, false)
