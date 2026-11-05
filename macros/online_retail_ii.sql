{# Exact duplicate lines are removed (same invoice, product, qty, time, price, customer). #}
{% macro ori_lines() %}
select distinct
    cast(invoice as varchar)                              as invoice,
    cast(stockcode as varchar)                            as stockcode,
    cast(quantity as integer)                             as quantity,
    cast(invoicedate as timestamp)                        as invoice_ts,
    cast(unitprice as double)                             as unit_price,
    nullif(trim(cast(customerid as varchar)), '')         as customer_id,
    country
from {{ source('online_retail_ii', 'transactions') }}
{% endmacro %}

{# Classify every line. Rules documented in docs/METRIC_RULES.md #}
{% macro ori_classified() %}
select
    *,
    quantity * unit_price as line_total,
    case
        when upper(invoice) like 'C%' then 'credit_note'
        when upper(invoice) like 'A%' then 'adjustment'
        else 'sale'
    end as invoice_type,
    -- a real product line: 5-digit stock code and a positive price
    (regexp_matches(stockcode, '^[0-9]{5}') and unit_price > 0) as is_product_line
from ({{ ori_lines() }})
{% endmacro %}
