-- One row per order, all money converted to GBP.
-- Business rules live HERE and nowhere else.
with items as (
    select order_id, sum(line_total) as items_total
    from {{ ref('stg_order_items') }}
    group by 1
),

refunds as (
    select order_id, sum(refund_amount) as refunded_total
    from {{ ref('stg_refunds') }}
    group by 1
)

select
    o.order_id,
    o.customer_id,
    o.ordered_at,
    o.order_date,
    o.status,
    o.currency,
    fx.rate_to_gbp,
    coalesce(i.items_total, 0)                         as items_total_local,
    o.discount                                         as discount_local,
    o.shipping_fee                                     as shipping_local,
    coalesce(r.refunded_total, 0)                      as refunded_local,
    -- product revenue: items minus discount, excludes shipping
    greatest(coalesce(i.items_total, 0) - o.discount, 0) * fx.rate_to_gbp
                                                       as gross_product_revenue_gbp,
    -- RULE: a refund can never exceed what the customer actually paid
    least(
        coalesce(r.refunded_total, 0) * fx.rate_to_gbp,
        greatest(coalesce(i.items_total, 0) - o.discount, 0) * fx.rate_to_gbp
    )                                                  as refunded_gbp,
    -- DQ flag: upstream refund system over-refunded vs amount paid
    (coalesce(r.refunded_total, 0)
        > greatest(coalesce(i.items_total, 0) - o.discount, 0) + 0.01)
                                                       as refund_exceeded_paid,
    o.shipping_fee * fx.rate_to_gbp                    as shipping_gbp
from {{ ref('stg_orders') }} o
left join items i   using (order_id)
left join refunds r using (order_id)
left join {{ ref('fx_rates') }} fx on fx.currency = o.currency
