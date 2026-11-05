{% if var('source_system', 'synthetic') == 'online_retail_ii' %}
-- Credit notes ("C..." invoices) are returns that do NOT say which original
-- invoice they reverse, so order_id is null ("unlinked"). They reduce revenue
-- on the day they are issued (see fct_daily_revenue).
select
    invoice                                 as refund_id,
    cast(null as varchar)                   as order_id,
    sum(abs(line_total))                    as refund_amount,
    min(invoice_ts)                         as refunded_at,
    cast(min(invoice_ts) as date)           as refund_date,
    'GBP'                                   as currency
from ({{ ori_classified() }})
where invoice_type = 'credit_note' and is_product_line
group by invoice
{% else %}
select
    cast(r.refund_id as varchar)            as refund_id,
    cast(r.order_id as varchar)             as order_id,
    cast(r.refund_amount as double)         as refund_amount,
    cast(r.refunded_at as timestamp)        as refunded_at,
    cast(r.refunded_at as date)             as refund_date,
    o.currency                              as currency
from {{ source('raw', 'refunds') }} r
left join {{ ref('stg_orders') }} o on cast(r.order_id as varchar) = o.order_id
{% endif %}
