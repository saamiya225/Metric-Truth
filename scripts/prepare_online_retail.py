"""Standardise a downloaded Online Retail II file for dbt.

Why this script exists: the same dataset circulates in several shapes (UCI .xlsx
with two sheets, Kaggle .csv copies) and with different column names
("Invoice" vs "InvoiceNo", "Price" vs "UnitPrice", "Customer ID" vs "CustomerID").
This script accepts any of them and writes ONE predictable CSV that dbt reads.

Usage:
    python scripts/prepare_online_retail.py --input path/to/online_retail_II.xlsx
    python scripts/prepare_online_retail.py --input path/to/online_retail_II.csv
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

# canonical name -> accepted spellings (compared after lower-casing, symbols removed)
ALIASES = {
    "invoice": {"invoice", "invoiceno", "invoicenumber"},
    "stockcode": {"stockcode"},
    "description": {"description"},
    "quantity": {"quantity"},
    "invoicedate": {"invoicedate"},
    "unitprice": {"unitprice", "price"},
    "customerid": {"customerid", "customer"},
    "country": {"country"},
}
REQUIRED = ["invoice", "stockcode", "quantity", "invoicedate", "unitprice", "customerid"]


def norm(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(col).lower())


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map whatever spelling this file uses onto the canonical names."""
    mapping = {}
    for col in df.columns:
        for canon, names in ALIASES.items():
            if norm(col) in names and canon not in mapping.values():
                mapping[col] = canon
    return df.rename(columns=mapping)


def load(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)  # every sheet
        print(f"Read {len(sheets)} sheet(s): {list(sheets)}")
        # rename PER SHEET: sheets of one file can spell columns differently
        return pd.concat([rename_columns(d) for d in sheets.values()], ignore_index=True)
    return rename_columns(pd.read_csv(path, dtype=str, encoding_errors="replace"))


def main(src: Path, out: Path) -> None:
    df = load(src)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns {missing}. Found: {list(df.columns)}")
    if "description" not in df.columns:
        df["description"] = ""
    if "country" not in df.columns:
        df["country"] = ""

    n_in = len(df)
    # Customer ID often arrives as '13085.0' (float formatting) -> '13085'
    df["customerid"] = (df["customerid"].astype("string").str.strip()
                        .str.replace(r"\.0$", "", regex=True)
                        .replace({"nan": pd.NA, "": pd.NA, "<NA>": pd.NA}))
    df["invoice"] = df["invoice"].astype("string").str.strip()
    df["stockcode"] = df["stockcode"].astype("string").str.strip()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unitprice"] = pd.to_numeric(df["unitprice"], errors="coerce")
    df["invoicedate"] = pd.to_datetime(df["invoicedate"], errors="coerce")

    bad = df[["invoice", "stockcode", "quantity", "unitprice", "invoicedate"]].isna().any(axis=1)
    print(f"Rows read: {n_in:,}; rows with unreadable core fields (dropped): {int(bad.sum()):,}")
    df = df[~bad]

    cols = ["invoice", "stockcode", "description", "quantity", "invoicedate",
            "unitprice", "customerid", "country"]
    out.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(out, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"Wrote {len(df):,} rows -> {out}")
    print(f"Date range: {df.invoicedate.min()} .. {df.invoicedate.max()}")
    print(f"Rows without customer id: {df.customerid.isna().mean():.1%}")
    print(f"Credit-note rows (invoice starts with C): "
          f"{df.invoice.str.upper().str.startswith('C').sum():,}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("data/raw/online_retail_ii.csv"))
    a = ap.parse_args()
    main(a.input, a.output)
