-- ILLUSTRATION: three simulated ways to total the SAME generated data.
-- (These team queries are examples of common mistakes, not real company code.)
with raw_items as (
    select order_id, sum(quantity * unit_price) as items_total
    from read_csv_auto('data/raw/order_items.csv') group by 1
),
raw_orders as (   -- NOT deduplicated
    select * from read_csv_auto('data/raw/orders.csv')
)

select 'Product team  (all non-cancelled, no dedupe, no FX, incl. shipping)' as definition,
       round(sum(i.items_total + o.shipping_fee - o.discount), 0) as revenue
from raw_orders o join raw_items i using (order_id)
where o.status <> 'cancelled'

union all
select 'Marketing     (completed, deduped, no FX, ignores refunds)',
       round(sum(i.items_total - o.discount), 0)
from (select distinct * from raw_orders) o join raw_items i using (order_id)
where o.status = 'completed'

union all
select 'Finance (GOVERNED, fct_daily_revenue: GBP, net of refunds, no internal)',
       round(sum(net_revenue_gbp), 0)
from fct_daily_revenue
