{% if var('source_system', 'synthetic') == 'online_retail_ii' %}
select
    invoice                 as order_id,
    stockcode               as product_id,
    quantity,
    unit_price,
    line_total
from ({{ ori_classified() }})
where invoice_type = 'sale' and is_product_line
  and invoice in (select order_id from {{ ref('stg_orders') }})
{% else %}
select
    cast(order_id as varchar)               as order_id,
    product_id,
    quantity,
    cast(unit_price as double)              as unit_price,
    quantity * cast(unit_price as double)   as line_total
from {{ source('raw', 'order_items') }}
{% endif %}
