{% if var('source_system', 'synthetic') == 'online_retail_ii' %}
select
    customer_id,
    cast(null as varchar)       as email,
    max(country)                as country,
    min(invoice_ts)             as signed_up_at,     -- first purchase seen
    false                       as is_internal
from ({{ ori_classified() }})
where customer_id is not null
group by 1
{% else %}
select
    cast(customer_id as varchar)    as customer_id,
    lower(email)                    as email,
    country,
    cast(signup_ts as timestamp)    as signed_up_at,
    is_internal
from {{ source('raw', 'customers') }}
{% endif %}
