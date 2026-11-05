"""Check the Online Retail II adapter against numbers computed BY HAND from
tests/fixtures/online_retail_ii_sample.csv (see docs/METRIC_RULES.md)."""
import sys
import duckdb

c = duckdb.connect("warehouse_fixture.duckdb", read_only=True)
orders, cust, net, gross = c.execute(
    "select sum(orders), count(*) filter (where customers>0), sum(net_revenue_gbp), "
    "sum(gross_revenue_gbp) from fct_daily_revenue").fetchone()
by_day = dict(c.execute("select cast(order_date as varchar), round(net_revenue_gbp,2) "
                        "from fct_daily_revenue").fetchall())
expected_days = {"2009-12-01": 290.40, "2009-12-02": 27.90, "2009-12-03": 29.50}
checks = {
    "orders == 5": orders == 5,
    "gross == 383.20": abs(gross - 383.20) < 0.01,
    "net == 347.80 (gross - 35.40 credit note)": abs(net - 347.80) < 0.01,
    "per-day net matches": by_day == expected_days,
}
for k, v in checks.items():
    print(("PASS " if v else "FAIL ") + k)
sys.exit(0 if all(checks.values()) else 1)
