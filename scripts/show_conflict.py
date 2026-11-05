"""Print naive revenue definitions next to the governed one.

    python scripts/show_conflict.py --source synthetic
    python scripts/show_conflict.py --source online_retail_ii
"""
import argparse
from pathlib import Path

import duckdb

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="synthetic", choices=["synthetic", "online_retail_ii"])
ap.add_argument("--db", default=None)
a = ap.parse_args()

db = a.db or f"warehouse_{a.source}.duckdb"
sql = Path(f"analyses/conflicting_definitions_{a.source}.sql").read_text()
rows = duckdb.connect(db, read_only=True).execute(sql).fetchall()

print(f"\nSource: {a.source}")
print(f"{'Definition':<100} {'Revenue (GBP)':>15}")
print("-" * 116)
for d, r in rows:
    print(f"{d:<100} {r:>15,.0f}")
hi, lo = max(r for _, r in rows), min(r for _, r in rows)
if lo:
    print(f"\nSpread between highest and lowest: {hi-lo:,.0f} ({(hi-lo)/abs(lo):.1%})")
