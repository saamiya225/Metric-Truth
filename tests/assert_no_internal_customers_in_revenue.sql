select f.order_id
from {{ ref('fct_orders') }} f
join {{ ref('dim_customers') }} c using (customer_id)
where c.is_internal
