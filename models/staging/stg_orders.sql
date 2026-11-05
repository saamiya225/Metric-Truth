{% if var('source_system', 'synthetic') == 'online_retail_ii' %}
-- One order per sales invoice that contains at least one real product line.
-- Real data has no status column, so every such invoice is 'completed'.
select
    invoice                                                   as order_id,
    max(customer_id)                                          as customer_id,
    min(invoice_ts)                                           as ordered_at,
    cast(min(invoice_ts) as date)                             as order_date,
    'completed'                                               as status,
    'GBP'                                                     as currency,
    coalesce(sum(line_total) filter (where stockcode in ('POST', 'DOT')), 0)
                                                              as shipping_fee,
    0.0                                                       as discount
from ({{ ori_classified() }})
where invoice_type = 'sale'
group by invoice
having bool_or(is_product_line)
{% else %}
with ranked as (
    select *, row_number() over (partition by order_id order by order_ts) as rn
    from {{ source('raw', 'orders') }}
)
select
    cast(order_id as varchar)              as order_id,
    cast(customer_id as varchar)           as customer_id,
    cast(order_ts as timestamp)            as ordered_at,
    cast(order_ts as date)                 as order_date,
    status,
    currency,
    cast(shipping_fee as double)           as shipping_fee,
    cast(discount as double)               as discount
from ranked
where rn = 1
{% endif %}
