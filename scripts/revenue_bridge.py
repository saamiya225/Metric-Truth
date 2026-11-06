"""Bridge from the naive total to the governed total, one rule at a time.

For each rule it reports how many rows it removes and how much the total moves,
so you can see which rules matter. The last line must equal the governed number
in the warehouse; if it does not, the rules and the SQL have drifted apart.

    python scripts/revenue_bridge.py
"""
import argparse

import duckdb

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="data/raw/online_retail_ii.csv")
ap.add_argument("--db", default="warehouse_online_retail_ii.duckdb")
a = ap.parse_args()

c = duckdb.connect()
c.execute(f"""
create temp view lines_all as
select invoice, stockcode,
       cast(quantity as double) as q, cast(unitprice as double) as p,
       invoicedate, customerid, country
from read_csv_auto('{a.csv}', all_varchar=true)
""")
c.execute("""
create temp view lines_d as
select distinct invoice, stockcode, q, p, invoicedate, customerid, country
from lines_all
""")

PRODUCT = "regexp_matches(stockcode, '^[0-9]{5}') and p > 0"
NOT_ADJ = "upper(invoice) not like 'A%'"
IS_CREDIT = "upper(invoice) like 'C%'"


def total(frm, where="true"):
    return c.execute(f"select coalesce(sum(q*p),0), count(*) from {frm} where {where}").fetchone()


# Each step: (label, table, rows kept by this step's rule)
steps = [
    ("Start: every row, nothing removed (Naive A)", "lines_all", "true"),
    ("Remove exact duplicate lines", "lines_d", "true"),
    ("Remove accounting adjustments (invoices starting 'A')", "lines_d", NOT_ADJ),
    ("Remove non-product lines on sales invoices (postage, fees, manual, zero price)",
     "lines_d", f"{NOT_ADJ} and ({IS_CREDIT} or ({PRODUCT}))"),
    ("Remove non-product lines on credit notes -> GOVERNED",
     "lines_d", f"{NOT_ADJ} and ({PRODUCT})"),
]

print(f"\n{'Step':<82} {'Rows removed':>13} {'Change (GBP)':>14} {'Running total':>15}")
print("-" * 128)
prev_total, prev_rows = None, None
for label, frm, where in steps:
    t, n = total(frm, where)
    if prev_total is None:
        print(f"{label:<82} {'':>13} {'':>14} {t:>15,.0f}")
    else:
        print(f"{label:<82} {prev_rows - n:>13,} {t - prev_total:>14,.0f} {t:>15,.0f}")
    prev_total, prev_rows = t, n

try:
    w = duckdb.connect(a.db, read_only=True)
    gov = w.execute("select sum(net_revenue_gbp) from fct_daily_revenue").fetchone()[0]
    diff = prev_total - gov
    print(f"\nGoverned total in warehouse: {gov:,.0f}")
    print(f"Bridge ends at:              {prev_total:,.0f}   (difference {diff:,.2f})")
    print("RECONCILED" if abs(diff) < 1 else "NOT RECONCILED: investigate before trusting the bridge")
except Exception as e:  # warehouse missing: still show the bridge
    print(f"\n(Could not compare with warehouse: {e})")
