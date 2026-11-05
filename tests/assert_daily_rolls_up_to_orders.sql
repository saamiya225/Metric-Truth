-- fct_daily_revenue must equal: revenue orders minus unlinked returns.
with a as (select sum(net_revenue_gbp) as v from {{ ref('fct_orders') }}),
     u as (
        select coalesce(sum(r.refund_amount * fx.rate_to_gbp), 0) as v
        from {{ ref('stg_refunds') }} r
        join {{ ref('fx_rates') }} fx on fx.currency = r.currency
        where r.order_id is null
     ),
     b as (select sum(net_revenue_gbp) as v from {{ ref('fct_daily_revenue') }})
select a.v, u.v, b.v from a, u, b where abs(a.v - u.v - b.v) > 0.01
