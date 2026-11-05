select
    customer_id,
    email,
    country,
    signed_up_at,
    is_internal
from {{ ref('stg_customers') }}
