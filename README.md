# metric-truth

## Overview

A dbt and DuckDB project that answers a deceptively simple question: how much did a
retailer actually sell?

I built it around a real dataset of retail transactions, and the answer turned out to
depend on a handful of decisions that are easy to get wrong and easy to hide. The
project writes those decisions down once, applies them the same way every time, and
checks the result with automated tests.

## Problem Statement

Raw transaction data can't just be added up. The file I used mixes genuine sales with
returns stored as negative lines, postage and fees, accounting write-offs and
duplicated lines. Anyone who totals it without deciding how to treat each of those
gets a different number, and two people can both believe theirs is right.

My goal was a single place where those rules live, so that every report reads from the
same table and a change to a rule is a one-file edit.

## Dataset

I used **Online Retail II** from the UCI Machine Learning Repository (CC BY 4.0), which
covers a UK online gift retailer from December 2009 to December 2011.
Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii. The file isn't
included here.

| | |
|---|---|
| Invoice lines | 1,067,371 |
| Date range | 2009-12-01 to 2011-12-09 |
| Lines with no customer ID | 22.8% |
| Credit-note lines (returns) | 19,494 (1.8%) |

It's a single flat table, with no status column and no refunds table, so most of the
work was working out what each kind of line means.

## Approach and Architecture

```
raw file -> staging -> intermediate -> marts
            clean up     business        fct_orders
            and          rules           fct_daily_revenue   <- reports read this
            standardise  live here       fct_monthly_active_customers
```

Each layer does one job. All the business rules sit in two models
(`int_order_totals` and `fct_orders`), so there's one place to look and one place to
change. The final table has one row per day with orders, customers, gross revenue,
refunds and net revenue.

I also made the pipeline work with two sources through a single switch. One is the real
retailer data. The other is a data generator I wrote that plants known flaws, which
let me test the rules against answers I knew in advance. Everything after the staging
layer is shared between them.

## Results

### Total Revenue by Definition

I totalled the same file three ways:

| Definition | Revenue (GBP) | vs governed |
|---|---|---|
| Add up every row | 19,287,251 | +1.9% |
| Sales invoices only, every line, returns ignored | 20,813,918 | +10.0% |
| **Governed: product lines only, duplicates removed, net of returns** | **18,925,714** | |

### Revenue Bridge

To see which rules do the work, I wrote a script that steps from the first total to the
governed one a rule at a time, computed separately from the dbt models:

| Step | Rows removed | Change (GBP) | Running total |
|---|---|---|---|
| Every row | | | 19,287,251 |
| Remove exact duplicate lines | 34,337 | -432,269 | 18,854,982 |
| Remove accounting adjustments (invoices starting "A") | 6 | +147,614 | 19,002,596 |
| Remove non-product lines on sales invoices | 10,712 | -822,506 | 18,180,090 |
| Remove non-product lines on credit notes | 1,190 | +745,625 | 18,925,714 |

It ends exactly on the figure in the warehouse.

### Key Findings

- **The net difference hides large corrections.** Adding up everything is only 1.9% off
  the governed number, but the individual rules move the total by about £2.15M in
  gross terms. Errors in opposite directions cancel, so a sloppy method can look
  accurate by luck.
- **Six rows matter.** The accounting adjustments are just six lines and move the total by
  £148K.
- **Non-product lines are large on both sides.** Postage, fees and manual entries add
  £0.82M of charges and £0.75M of credits, which net to about £77K. Excluding them
  from both sides is consistent, but I haven't yet looked at what they actually are.

### What the Governed Figure Means

The first two totals are wrong in principle, not just different. Ignoring returns counts
money that went back to customers as revenue. Adding every row counts postage, fees and
write-offs as sales, and its total only looks reasonable because those errors partly
cancel. The governed figure is the one I can defend line by line, but I'd describe it as
net product sales under the rules below, not as the retailer's true revenue. "Revenue" can
mean net product sales, accounting revenue or cash received, and these are different
numbers, which is why I wrote the definition down.

## Business Rules and Assumptions

These are my rules, not facts from the dataset. The full list is in
[`docs/METRIC_RULES.md`](docs/METRIC_RULES.md).

| Decision | Why |
|---|---|
| Revenue counts only product lines: a 5-digit stock code and a price above zero | Postage, manual entries and bank charges aren't product sales |
| Every invoice is treated as a completed sale | The data has no status column |
| Credit notes reduce revenue on the day they're issued | They don't say which invoice they reverse |
| Orders with no customer ID still count as revenue, but not as active customers | The money was real; I just can't attribute it to a person |
| Exact duplicate lines count once | Likely ingestion repeats |

## Open Questions

The governed figure depends on four assumptions that I took from the dataset documentation
and haven't yet checked against the data. The reconciliation shows the code follows these
rules, not that they're right.

| Assumption | If it's wrong |
|---|---|
| Exact duplicate lines are errors | If they're genuine repeat scans, revenue is about £0.43M (2.3%) higher |
| Non-product lines (postage, manual entries, fees) aren't revenue | If some are customer discounts, excluding them overstates revenue. I haven't broken them down by stock code yet, so the effect is unknown |
| Every invoice is a completed sale | The data has no status column, so some invoices may be cancelled orders. Effect unknown |
| Credit notes reduce revenue on the day they're issued | The data doesn't link them to original invoices, so the timing could differ from the retailer's own accounting. Effect unknown |

The next step is to measure how sensitive the total is to each one.

## Testing and Validation

- **26 dbt tests** run on every build: uniqueness, non-null keys, valid values,
  relationships between tables, and custom checks that the daily table reconciles to the
  orders table, no staff accounts appear in revenue, and a refund never exceeds what the
  customer paid.
- **A generated dataset with planted flaws** (duplicates, test orders, mixed currencies,
  late refunds). One of the tests caught a real mistake in my first version: full refunds
  ignored the discount, which made net revenue negative on 469 orders. I fixed it with an
  explicit rule that a refund can't exceed the amount paid.
- **A 13-row file in the real dataset's format**, with a credit note, a postage line, a
  duplicate and an adjustment, where I worked out the correct answer by hand
  (5 orders, £347.80 net). Writing it also exposed a bug in how I read Excel files with
  differently named columns.
- A GitHub Actions workflow runs the generated-data build and the 13-row check on every
  push.

On the real data the tests are mostly structural, since some can't fail by design. They
catch regressions. The bridge is the more meaningful check.

## Usage

```bash
python3 -m venv .venv && source .venv/bin/activate
make setup

make all                                   # generated data, end to end

# real data: download Online Retail II from the link above first
make prepare INPUT=path/to/online_retail_II.xlsx
make build test conflict SOURCE=online_retail_ii
python scripts/revenue_bridge.py           # step-by-step bridge

make fixture                               # 13-row hand-checked test
```

## Limitations and Future Work

It's a batch pipeline that runs on demand, which suits a question about agreed rules
more than about speed. With more time I'd break down the non-product stock codes, test
how sensitive the total is to the duplicate and discount assumptions, add a chart of
the bridge, run it on a schedule with incremental models, and look at whether credit
notes can be matched to their original invoices.

## Repository Structure

```
models/        staging, intermediate and mart layers
macros/        reusable SQL for the real-data source
tests/         custom reconciliation tests and the 13-row fixture
analyses/      the naive-versus-governed comparison queries
scripts/       data generator, file preparation, reports, revenue bridge
docs/          written metric rules
```

Dataset: Online Retail II, UCI Machine Learning Repository, CC BY 4.0.