-- Active customer = at least one revenue order in the calendar month.
-- Orders with no customer id cannot be counted as a person.
select
    date_trunc('month', order_date)  as month,
    count(distinct customer_id)      as active_customers
from {{ ref('fct_orders') }}
where customer_id is not null
group by 1
