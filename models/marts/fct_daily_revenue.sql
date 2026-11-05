-- THE metric table. Every dashboard should read from here.
-- net revenue = revenue orders (net of refunds linked to an order)
--             - unlinked returns (credit notes, recognised on the day issued)
with sales as (
    select
        order_date,
        count(*)                        as orders,
        count(distinct customer_id)     as customers,
        sum(gross_product_revenue_gbp)  as gross_revenue_gbp,
        sum(refunded_gbp)               as linked_refunds_gbp,
        sum(net_revenue_gbp)            as net_sales_gbp
    from {{ ref('fct_orders') }}
    group by 1
),

unlinked as (
    select
        r.refund_date                        as order_date,
        sum(r.refund_amount * fx.rate_to_gbp) as unlinked_returns_gbp
    from {{ ref('stg_refunds') }} r
    join {{ ref('fx_rates') }} fx on fx.currency = r.currency
    where r.order_id is null
    group by 1
)

select
    coalesce(s.order_date, u.order_date)                         as order_date,
    coalesce(s.orders, 0)                                        as orders,
    coalesce(s.customers, 0)                                     as customers,
    coalesce(s.gross_revenue_gbp, 0)                             as gross_revenue_gbp,
    coalesce(s.linked_refunds_gbp, 0)
        + coalesce(u.unlinked_returns_gbp, 0)                    as refunds_gbp,
    coalesce(s.net_sales_gbp, 0)
        - coalesce(u.unlinked_returns_gbp, 0)                    as net_revenue_gbp,
    (coalesce(s.net_sales_gbp, 0) - coalesce(u.unlinked_returns_gbp, 0))
        / nullif(s.orders, 0)                                    as avg_order_value_gbp
from sales s
full outer join unlinked u on s.order_date = u.order_date
