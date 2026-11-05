# metric-truth: one tested definition of "revenue"

A dbt + DuckDB project that turns messy retail transaction data into trustworthy
revenue metrics, using one written set of business rules that is enforced by
automated tests.

It runs on **two data sources** and produces identical tables from either:

| Source | What it is | Used for |
|---|---|---|
| `online_retail_ii` | Real invoice lines from a UK online retailer (1,067,371 rows, Dec 2009 to Dec 2011) | The main analysis |
| `synthetic` | Generated shop data with known, planted flaws | Demos, tests and CI |

## The problem

Raw transaction data cannot simply be summed into "revenue". In the real dataset,
the same table mixes genuine sales with:

- **Returns**, stored as negative lines (19,494 credit-note rows)
- **Postage and fees**, and accounting adjustments that are not product sales
- **Duplicated lines**
- **Orders with no customer ID** (22.8% of rows)

Unless the rule for each of these is written down and enforced, anyone totalling
the data gets a different answer.

## Hypothesis

If the rules live in one tested layer, then:

1. every report can read one table (`fct_daily_revenue`) and reconcile to it,
2. naive totals differ materially from the governed figure, and
3. data problems fail a test before they reach a dashboard.

## Dataset

**Online Retail II**, UCI Machine Learning Repository, licensed CC BY 4.0.
Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii (see that page for
the full citation). The raw file is **not** included in this repository.

Profile of the file as loaded by `scripts/prepare_online_retail.py`:

| Measure | Value |
|---|---|
| Rows read | 1,067,371 |
| Rows dropped as unreadable | 0 |
| Date range | 2009-12-01 to 2011-12-09 |
| Rows without a customer ID | 22.8% |
| Credit-note rows (invoice starts with "C") | 19,494 |

## Results

### Real data (Online Retail II)

> run `make build test conflict SOURCE=online_retail_ii` 

| Definition | Revenue (GBP) |
|---|---|
| Naive A: sum of quantity x price over every row |      |
| Naive B: sales invoices only, all lines, returns ignored |       |
| **Governed**: product lines, deduplicated, net of credit notes |       |

- Spread between highest and lowest: _TODO_
- dbt tests passed: _TODO_ / _TODO_
- Findings and rule changes made after seeing the real data: _TODO_

### Generated data (illustration)

The generated data has known flaws, so it proves the rules work when the right
answer is known. The three "team" queries are **simulated examples of common
mistakes**, not real company code.

| Definition | Revenue |
|---|---|
| Naive: all non-cancelled, no dedupe, no FX, includes shipping | £13.0M |
| Naive: completed, deduplicated, no FX, ignores refunds | £11.4M |
| **Governed**: GBP, net of refunds, excludes internal/test | **£9.9M** |

A 31% spread, with all 26 dbt tests passing.

A test caught a real bug during the build: full refunds ignored the discount, so
net revenue went negative on 469 orders. The fix is a stated rule, *a refund cannot
exceed the amount paid*, capped in `int_order_totals`, with a
`refund_exceeded_paid` flag so the upstream issue stays visible.

## How it works

```
raw data ──► staging ──► intermediate ──► marts
             (clean,      (business        dim_customers
              dedupe,      rules, GBP,     fct_orders
              one shape    refund cap)     fct_daily_revenue  ◄── dashboards read this
              per source)                  fct_monthly_active_customers
```

Each layer has one job. Business rules live **once**, in `int_order_totals` and
`fct_orders`, so changing a rule is a single edit. A source switch
(`SOURCE=synthetic` or `SOURCE=online_retail_ii`) selects which staging logic runs;
everything after staging is shared.

The rules for each source are documented in [`docs/METRIC_RULES.md`](docs/METRIC_RULES.md).
Key decisions:

- Shipping and non-product lines (postage, manual entries, bank charges) are not revenue.
- Credit notes reduce revenue on the day they are issued. The data does not say
  which invoice each one reverses, so they are not linked to orders.
- Orders with no customer ID still count as revenue but not as active customers.
- Exact duplicate lines are removed.

## Run it

**Setup (once):**
```bash
python3 -m venv .venv
source .venv/bin/activate
make setup
```

**Generated data (no download):**
```bash
make all
```

**Real data:**
1. Download Online Retail II from the UCI page above and save it outside git
   (this repo ignores `data/`).
2. Standardise and build:
```bash
make prepare INPUT=path/to/online_retail_II.xlsx
make build test conflict SOURCE=online_retail_ii
```

**Check the real-data code without downloading anything:**
```bash
make fixture
```
This runs the real-data path on a 13-row hand-made file whose correct answers were
worked out by hand. CI runs it on every push.

## Project structure

```
metric-truth/
├── models/
│   ├── staging/         clean-up, one file per table, handles both sources
│   ├── intermediate/    business rules
│   └── marts/           final tables
├── macros/              reusable SQL for the real-data source
├── tests/               custom reconciliation tests and the hand-checked fixture
├── analyses/            naive-vs-governed comparison queries
├── scripts/             data generator, real-data preparation, reports
├── docs/METRIC_RULES.md the written metric definitions
└── Makefile             one-word commands
```

## Tests

26 automated checks run on every build:

- **Generic:** unique, not null, accepted values, relationships, non-negative.
- **Custom reconciliation:** the daily table equals orders minus unlinked returns;
  no internal customers in revenue; refunds never exceed the amount paid.

## Limitations

- **Batch, not real time.** It runs on demand, not as events arrive.
- **Assumptions about the real data.** Every real invoice is treated as
  `completed` because there is no status column, and credit notes are matched to
  a day rather than to the invoice they reverse. See `docs/METRIC_RULES.md`.
- **Static exchange rates** in the generated-data demo. Real FX would be daily and
  joined on order date.
- **Generated data is not a real business**, so its totals illustrate the method only.

## At larger scale

Incremental models partitioned by date, a scheduler (Airflow or Dagster),
`dbt source freshness` checks, slim CI using `state:modified+`, a cloud warehouse
such as BigQuery or Snowflake (an adapter swap), and the dbt Semantic Layer for
metric definitions.

## Credits

Dataset: Online Retail II, UCI Machine Learning Repository (CC BY 4.0).