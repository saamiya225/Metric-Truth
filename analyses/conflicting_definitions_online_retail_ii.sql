-- Naive ways to total the REAL retailer's data vs the governed number.
with raw as (select * from read_csv_auto('data/raw/online_retail_ii.csv', all_varchar=true))
select 'Naive A: sum(quantity x price) over every row (returns, fees, adjustments, duplicates all in)' as definition,
       round(sum(cast(quantity as double) * cast(unitprice as double)), 0) as revenue
from raw
union all
select 'Naive B: sales invoices only, every line (fees and non-product lines in, returns ignored)',
       round(sum(cast(quantity as double) * cast(unitprice as double)), 0)
from raw where upper(invoice) not like 'C%'
union all
select 'GOVERNED (fct_daily_revenue): product lines, deduped, net of credit notes',
       round(sum(net_revenue_gbp), 0)
from fct_daily_revenue
