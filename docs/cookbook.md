---
title: Cookbook
description: Task-shaped PyPlyne recipes for common data pipeline workflows.
---

# Cookbook

These recipes are task-shaped patterns you can adapt while working
interactively. They follow the same idea as data-tool cookbooks: start from the
job you need done, show the smallest complete pipeline, then call out the
assumptions that matter when you change it.

## Assumptions

- Commands run from the project root with `uv run pyplyne path/to/file.pyplyne`, or
  against a warm session with `uv run pyplyne send --expr '...'`.
- Example filenames such as `sales.csv`, `orders.json`, and `sales.xlsx` are
  placeholders. Replace them with paths that exist in your project.
- Example table columns use common names: `region`, `amount`, `discount`,
  `customer_id`, `order_id`, and `status`.
- `df` pipelines use table verbs: `where`, `mutate`, `select`, `group_by`,
  `summarize`, and `arrange`.
- `seq` pipelines use Python-iterable verbs: `map`, `filter`, `reduce`,
  `set_fields`, `drop_fields`, and `keep_fields`.
- Use `to_rows()` and `to_table()` at the boundary between table work and
  record-by-record work.
- File reads and table writes use Polars. Sequence JSON/CSV writes are
  Python-backed, which is useful when you have JSON-like row dictionaries.
  Pass format-specific options to `read_csv`, `read_json`, `read_parquet`,
  `read_excel`, and their matching write helpers when you need them.

## Recipe Index

| Task | Use When |
| --- | --- |
| [Clean and summarize a CSV](#clean-and-summarize-a-csv) | You need a report-ready aggregate from raw rows. |
| [Write one result to several formats](#write-one-result-to-several-formats) | You need the same result for humans, pipelines, and archives. |
| [Build a JSON review queue](#build-a-json-review-queue) | You need row dictionaries for an app, API, or manual workflow. |
| [Summarize JSON records as a table](#summarize-json-records-as-a-table) | You have JSON-like data but want table aggregation. |
| [Normalize records before table work](#normalize-records-before-table-work) | You need to add, drop, or keep fields before converting to a table. |
| [Convert Excel to Parquet](#convert-excel-to-parquet) | You received a workbook but want a columnar output file. |
| [Keep data warm in a session](#keep-data-warm-in-a-session) | You are iterating on the same data repeatedly. |
| [Use a Python function in a pipeline](#use-a-python-function-in-a-pipeline) | You already have Python logic and want to compose it with PyPlyne. |

## Clean And Summarize A CSV

**When to use this:** you have raw tabular data and need a grouped result for a
dashboard, export, or quick check.

```pyplyne
sales = df read_csv("sales.csv")

regional_summary = sales
  |> where(amount > 0)
  |> mutate(net=amount - discount)
  |> group_by(region)
  |> summarize(
    total=sum(net),
    average=mean(net),
    smallest=min(net),
    largest=max(net),
    rows=count(),
  )
  |> arrange(region)
```

**Adapt it:** filter before `group_by(...)` when the condition removes rows from
the source data. Always follow `group_by(...)` with `summarize(...)` before you
materialize or assign the result.

## Write One Result To Several Formats

**When to use this:** you want one cleaned table to feed different consumers.
For example, CSV for a person, Parquet for another pipeline, and JSON for an app.

```pyplyne
summary = df read_csv("sales.csv")
  |> where(amount > 100)
  |> mutate(net=amount - discount)
  |> group_by(region)
  |> summarize(total=sum(net), rows=count())
  |> arrange(region)

summary
  |> write_csv("build/regional_summary.csv")
  |> write_parquet("build/regional_summary.parquet")
  |> write_json("build/regional_summary.json")
```

**Adapt it:** write helpers preserve the current value, so you can chain them
when each output should contain the same table. Split the chain into separate
assignments if each output needs different columns or filters.

## Build A JSON Review Queue

**When to use this:** you need to leave table mode, annotate individual records,
and hand the result to a review tool or API.

```pyplyne
review_queue = df read_csv("sales.csv")
  |> where(amount > 100)
  |> select(region, amount, discount)
  |> to_rows()
  |> set_fields(
    net=amount - discount,
    reviewed=False,
    label=region + "-" + str(amount),
  )
  |> keep_fields(region, amount, net, reviewed, label)

review_queue |> write_json("review_queue.json")
```

**Adapt it:** `to_rows()` changes the pipeline from a table into a sequence of
row dictionaries. After that boundary, use sequence helpers such as
`set_fields(...)` and `keep_fields(...)` instead of table verbs.

## Summarize JSON Records As A Table

**When to use this:** you have JSON data but want grouped table calculations.
`read_json(...)` returns a table, so convert to rows only if you need
record-by-record cleanup first.

```pyplyne
orders = df read_json("orders.json")

paid_orders = orders
  |> to_rows()
  |> set_fields(net=amount - discount)
  |> keep_fields(region, customer_id, status, net)
  |> to_table()
  |> where(status == "paid")

paid_summary = paid_orders
  |> group_by(region)
  |> summarize(total=sum(net), customers=count())
  |> arrange(region)
```

**Adapt it:** keep the first stage as `df read_json(...)` when the JSON file is
already table-shaped. Use `seq` only when you start from an existing Python
iterable or literal list of records.

## Normalize Records Before Table Work

**When to use this:** you have records from Python, an API, or a previous
`to_rows()` step and need to shape them before table aggregation.

```pyplyne
clean_rows = seq orders
  |> drop_fields(debug, raw_payload)
  |> set_fields(
    net=amount - discount,
    needs_review=amount > 1000,
  )
  |> keep_fields(order_id, region, amount, net, needs_review)

review_summary = clean_rows
  |> to_table()
  |> group_by(region)
  |> summarize(
    total=sum(net),
    review_rows=sum(needs_review),
    rows=count(),
  )
```

**Adapt it:** use record helpers for field cleanup and table verbs for column
math, filtering, sorting, and aggregation. The explicit `to_table()` call makes
that switch visible.

## Convert Excel To Parquet

**When to use this:** a workbook is the input format, but you want a compact
table file for repeatable processing.

```pyplyne
clean = df read_excel("sales.xlsx")
  |> where(amount > 0)
  |> mutate(net=amount - discount)
  |> select(region, amount, discount, net)

clean |> write_parquet("sales_clean.parquet")
```

Excel support depends on the optional Excel dependencies:

```bash
uv sync --extra excel
```

**Adapt it:** pass the same kind of keyword options you would pass to Polars
when you need a specific sheet, schema behavior, or file-format setting.

## Keep Data Warm In A Session

**When to use this:** you are trying several transformations against the same
loaded data and do not want to reload it for every experiment.

Start the server once:

```bash
uv run pyplyne serve --port 8765 --load setup.pyplyne
```

Then send complete expressions:

```bash
uv run pyplyne send --expr 'sales |> where(amount > 100) |> select(region, amount)'
uv run pyplyne send --expr 'sales |> group_by(region) |> summarize(total=sum(amount), rows=count())'
```

**Adapt it:** put stable setup in `setup.pyplyne`, then keep `send --expr` calls
small. If you use `group_by(...)`, include the matching `summarize(...)` in the
same expression.

## Use A Python Function In A Pipeline

**When to use this:** Python already has the domain logic and PyPlyne is the
composition layer.

Seed a session from Python:

```python
from pyplyne import PyPlyneSession
from scoring import score_order

session = PyPlyneSession({"orders": orders, "score_order": score_order})
session.run("""
ranked = seq orders
  |> map(score_order(_))
""")
```

Or import from a PyPlyne file when the function is available on `PYTHONPATH`:

```pyplyne
from scoring import score_order

ranked = seq orders
  |> map(score_order(_))
```

**Adapt it:** custom Python functions fit most naturally in `seq` pipelines,
where each item can be passed into ordinary Python code. Convert a table with
`to_rows()` first if the function expects dictionaries.
