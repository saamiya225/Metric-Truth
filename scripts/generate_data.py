"""Generate a deliberately messy e-commerce dataset.

The mess is intentional. Each flaw maps to a metric definition that different
teams get wrong, so the dbt project has something real to fix:

  * ~2% duplicated order rows (ingestion retries)
  * internal / test accounts placing orders
  * cancelled and pending orders mixed with completed ones
  * multi-currency orders (GBP / EUR / USD)
  * partial and full refunds arriving after the order
  * shipping fees that are not product revenue
"""
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def main(n_customers: int, n_orders: int, seed: int, out: Path) -> None:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    start = datetime(2025, 1, 1)
    days = 365

    # --- customers -----------------------------------------------------
    customers = []
    for i in range(1, n_customers + 1):
        internal = rng.random() < 0.02
        customers.append({
            "customer_id": i,
            "email": f"user{i}@{'ourcompany.com' if internal else 'example.com'}",
            "country": rng.choice(["GB", "GB", "GB", "DE", "FR", "US"]),
            "signup_ts": (start + timedelta(days=rng.randint(0, days - 1),
                                            seconds=rng.randint(0, 86399))).isoformat(),
            "is_internal": internal,
        })
    cust_df = pd.DataFrame(customers)
    internal_ids = set(cust_df.loc[cust_df.is_internal, "customer_id"])

    # --- orders / items ------------------------------------------------
    products = {p: round(rng.uniform(5, 120), 2) for p in range(1, 61)}
    orders, items = [], []
    for oid in range(1, n_orders + 1):
        cid = rng.randint(1, n_customers)
        ts = start + timedelta(days=rng.randint(0, days - 1),
                               seconds=rng.randint(0, 86399))
        r = rng.random()
        status = ("completed" if r < 0.82 else
                  "cancelled" if r < 0.92 else "pending")
        if cid in internal_ids and rng.random() < 0.5:
            status = "test"
        country = cust_df.loc[cust_df.customer_id == cid, "country"].iat[0]
        currency = {"GB": "GBP", "DE": "EUR", "FR": "EUR", "US": "USD"}[country]
        orders.append({
            "order_id": oid, "customer_id": cid, "order_ts": ts.isoformat(),
            "status": status, "currency": currency,
            "shipping_fee": rng.choice([0, 0, 3.99, 4.99, 6.5]),
            "discount": round(rng.choice([0, 0, 0, 5, 10, 15]), 2),
        })
        for _ in range(rng.randint(1, 4)):
            pid = rng.choice(list(products))
            items.append({"order_id": oid, "product_id": pid,
                          "quantity": rng.randint(1, 3),
                          "unit_price": products[pid]})

    orders_df, items_df = pd.DataFrame(orders), pd.DataFrame(items)

    # --- refunds (completed orders only, arrive 1-30 days later) --------
    refunds = []
    totals = (items_df.assign(t=items_df.quantity * items_df.unit_price)
              .groupby("order_id").t.sum())
    for o in orders:
        if o["status"] == "completed" and rng.random() < 0.06:
            amt = totals[o["order_id"]]
            if rng.random() < 0.5:
                amt = round(amt * rng.uniform(0.2, 0.7), 2)
            refunds.append({
                "refund_id": len(refunds) + 1, "order_id": o["order_id"],
                "refund_amount": round(amt, 2),
                "refunded_at": (datetime.fromisoformat(o["order_ts"])
                                + timedelta(days=rng.randint(1, 30))).isoformat(),
            })
    refunds_df = pd.DataFrame(refunds)

    # --- inject duplicate order rows (retries) -------------------------
    dupes = orders_df.sample(frac=0.02, random_state=seed)
    orders_df = pd.concat([orders_df, dupes], ignore_index=True)
    orders_df = orders_df.sample(frac=1, random_state=seed).reset_index(drop=True)

    cust_df.to_csv(out / "customers.csv", index=False)
    orders_df.to_csv(out / "orders.csv", index=False)
    items_df.to_csv(out / "order_items.csv", index=False)
    refunds_df.to_csv(out / "refunds.csv", index=False)
    print(f"customers={len(cust_df)} orders={len(orders_df)} "
          f"(incl. {len(dupes)} duplicates) items={len(items_df)} "
          f"refunds={len(refunds_df)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--customers", type=int, default=5000)
    ap.add_argument("--orders", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    a = ap.parse_args()
    main(a.customers, a.orders, a.seed, a.out)
