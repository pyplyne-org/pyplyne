---
title: Language Guide
description: Practical guide to writing PyPlyne pipelines.
---

# Language Guide

This guide builds up the PyPlyne workflows you will use most often.
For a compact list of syntax and verbs, use the [Language Reference](reference.md).

PyPlyne has two main pipeline shapes:

| Shape | Use it for | Main verbs |
| --- | --- | --- |
| `seq` | Non-string, non-mapping Python iterables; Polars tables become row dictionaries | `map`, `filter`, `reduce`, `set_fields`, `drop_fields`, `keep_fields` |
| `df` | Polars-backed table data | `where`, `mutate`, `select`, `group_by`, `summarize`, `arrange` |

The shape determines which verbs are available and how expressions are
interpreted.

## Start With a Pipeline

The pipeline operator `|>` sends the value on the left into the call on the
right. Read it as "then":

```pyplyne
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)
```

The assignment stores the final result of the pipeline. In this example,
`numbers` is a sequence, so `filter` and `map` use sequence semantics.

Pipelines can also call methods on the current value:

```pyplyne
name = "pyplyne" |> .upper()
```

Shape annotations go on the right-hand side:

```pyplyne
values = seq [1, 2, 3]
sales = df read_csv("sales.csv")
```

Once a variable is known to be `seq` or `df`, later pipelines can start from
that variable without repeating the annotation:

```pyplyne
large_sales = sales |> where(amount > 100)
```

If a pipeline starts from an arbitrary Python expression or a custom function,
annotate the source so PyPlyne knows which verb family applies.

Shape annotations also validate or normalize values at runtime. `df [...]`
turns row dictionaries into a Polars DataFrame. `seq ...` checks that the value
is a non-string, non-mapping iterable rather than a single mapping, string-like
value, or scalar. Polars tables annotated as `seq` become row dictionaries.

## Work With Sequences

Use `seq` for non-string, non-mapping Python iterables. Sequence verbs evaluate
Python expressions over the items in the iterable:

```pyplyne
values = seq [1, 2, 3, 4]

doubled = values |> map(_ * 2)
evens = values |> filter(_ % 2 == 0)
total = values |> reduce(_1 + _2)
total_from_zero = values |> reduce(_1 + _2, 0)
```

The result shape depends on the verb:

- `map(expression)` returns one transformed item for each input item.
- `filter(expression)` keeps items where the expression is true.
- `reduce(expression)` combines the sequence into one scalar value.

Use `_` for the common one-argument case:

```pyplyne
values |> map(_ * 2)
values |> filter(_ > 2)
```

Use numbered placeholders when the callback receives more than one argument:

```pyplyne
values |> reduce(_1 + _2)
```

Use arrow lambdas when names make the expression easier to read:

```pyplyne
values |> map(x => x * 2)
values |> reduce((total, x) => total + x)
```

The older `fn x: x * 2` spelling is still accepted for compatibility.

For more examples with records, Python objects, functions, and missing fields,
see [Sequence Patterns](sequence-patterns.md).

## Work With Records

Sequences of dictionaries are common when working with JSON, APIs, or rows
converted from a table. Use sequence verbs to filter the records, then field
helpers to add, remove, or project fields:

```pyplyne
orders = seq [
  {"item": "notebook", "qty": 1, "price": 6},
  {"item": "coffee", "qty": 3, "price": 4},
  {"item": "pens", "qty": 2, "price": 3},
]

restock = orders
  |> filter(qty > 1)
  |> set_fields(total = qty * price, status = "buy")
  |> drop_fields(price)
  |> keep_fields(item, qty, total, status)
```

Record helpers:

- `set_fields(name = expression, ...)` adds or replaces fields.
- `drop_fields(field, ...)` removes fields when present.
- `keep_fields(field, ...)` projects records to selected fields.

Inside record `filter(...)` expressions, bare names can read dictionary fields
or object attributes on the current item. Inside `set_fields(...)`, bare names
read fields from row dictionaries, and the input rows must be dictionaries:

```pyplyne
orders |> filter(qty > 1)
orders |> set_fields(buy = item == "pens")
```

If a bare field or attribute is missing in a filter, equality and ordering
comparisons do not match, and `!=` does match:

```pyplyne
orders |> filter(qty > 1)
```

Rows without `qty` are skipped by `qty > 1`; rows without `item` match
`item != "pens"`. Missing fields are boolean-false, but arithmetic still
requires present values, so `set_fields(total = qty * price)` raises an error
when `qty` or `price` is missing.

If you pass a single bare name to `filter`, PyPlyne treats it as an existing
predicate function:

```pyplyne
orders |> filter(is_priority)
```

For field truthiness, use a comparison or explicit row access instead:

```pyplyne
orders |> filter(active == True)
orders |> filter(_["active"])
```

Inside `map(...)`, use placeholders or explicit lambdas:

```pyplyne
orders |> map(_["item"])
orders |> map(order => order["item"])
```

## Work With Tables

Use `df` for table-shaped data. PyPlyne normalizes table-shaped values into
Polars DataFrames and compiles table expressions to Polars expressions:

```pyplyne
sales = df [
  {"region": "north", "amount": 120, "discount": 10},
  {"region": "south", "amount": 80, "discount": 5},
  {"region": "north", "amount": 220, "discount": 20},
]

large_sales = sales
  |> where(amount > 100)
  |> mutate(net = amount - discount)
  |> select(region, amount, net)
```

Inside table verbs, bare names are columns:

```pyplyne
sales |> where(amount > 100 and region == "north")
```

Think of each table verb as a context for column expressions:

| Verb | Use it to |
| --- | --- |
| `where(condition)` | Filter rows by a boolean expression. |
| `mutate(name = expression, ...)` | Add or replace columns. |
| `select(column, ...)` | Choose columns. |
| `group_by(column, ...)` | Group rows before a summary. |
| `summarize(name = aggregation, ...)` | Aggregate grouped or whole tables. |
| `arrange(column, descending=True)` | Sort rows. |

Table expressions can use arithmetic, comparisons, and boolean logic:

```pyplyne
sales
  |> where(amount > 100 and discount < 20)
  |> mutate(net = amount - discount)
  |> arrange(net, descending=True)
```

## Summarize Tables

Use `group_by(...)` followed by `summarize(...)` when each group should become
one result row:

```pyplyne
summary = sales
  |> where(amount > 100)
  |> mutate(net = amount - discount)
  |> group_by(region)
  |> summarize(
    total = sum(net),
    average = mean(net),
    smallest = min(net),
    largest = max(net),
    rows = count(),
  )
  |> arrange(region)
```

The aggregation helpers available inside `summarize(...)` are `sum`, `mean`,
`min`, `max`, and `count`. A grouped table should be followed immediately by
`summarize(...)` before it is assigned, printed, written, or passed to other
verbs.

Without `group_by(...)`, `summarize(...)` aggregates the whole table:

```pyplyne
overall = sales
  |> summarize(total = sum(amount), rows = count())
```

## Read and Write Files

Read helpers create table-shaped values. Table writes use Polars writers, and
sequence JSON/CSV writes use Python-backed writers. Write helpers return the
current value so you can keep piping:

```pyplyne
sales = df read_csv("sales.csv")

summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total = sum(amount))

summary
  |> write_json("summary.json")
  |> write_parquet("summary.parquet")
  |> write_csv("summary.csv")
```

Supported formats are CSV, JSON, Parquet, and Excel. Excel support requires:

```bash
uv sync --extra excel
```

## Move Between Tables and Sequences

Use `to_rows()` to turn a table into a sequence of dictionaries, and
`to_table()` to turn records back into a Polars table:

```pyplyne
rows = sales |> to_rows()
table = rows |> to_table()
```

This is the explicit boundary between table verbs and sequence verbs. A common
pattern is to do column-oriented filtering first, cross to records for
dictionary-style edits, then return to a table:

```pyplyne
reviewed = sales
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
  |> arrange(region)
```

After `to_rows()`, use sequence verbs. After `to_table()`, use table verbs.

## Run Now or Defer

PyPlyne executes pipelines by default. Assigning a table pipeline gives you a
concrete Polars result, even if Polars lazy plans are used internally:

```pyplyne
large_sales = sales
  |> where(amount > 100)
  |> select(region, amount)
```

Use `defer` only when you want to keep a lazy query plan:

```pyplyne
plan = defer read_csv("sales.csv")
  |> where(amount > 100)
  |> select(region, amount)
```

Avoid wrapping a lazy plan in `df` when you want to keep it lazy, because `df`
normalization can collect lazy frames.

`collect()` remains available for lazy Polars plans:

```pyplyne
result = plan |> collect()
```

## Use Python Objects

Python imports work normally:

```pyplyne
from pathlib import Path
import polars as pl

root = Path(".")
sales = df pl.DataFrame([
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
])
```

Custom Python functions can be used in sequence pipelines:

```pyplyne
from scoring import score_order

ranked = seq orders
  |> map(score_order(_))
```

Custom pipeline functions and method pipes do not change PyPlyne's shape
tracking. If a custom function changes a table into rows, or rows into a table,
start the next pipeline with an explicit `seq` or `df` boundary.

They can also be called before a shape annotation:

```pyplyne
orders = seq load_orders()
```

## Know the Two Uses of `_`

Inside sequence verbs, `_` is the current item:

```pyplyne
values |> map(_ * 10)
```

In an interactive session, `_` is also the last expression result:

```pyplyne
values |> map(_ * 10)
_ |> filter(_ > 10)
```

In the second line, the left `_` is the previous result and the right `_` is
the current item inside `filter`:

```text
_ |> filter(_ > 10)
^          ^
last       current
result     item
```

The session only stores shape information for `_` when the last result is
sequence-shaped or table-shaped.

## Expression Basics

PyPlyne currently supports:

- assignments: `name = expression`
- shape annotations: `name = seq expression`, `name = df expression`
- lists, tuples, dictionaries, strings, numbers, booleans, and `None`
- function calls: `name(arg, key=value)`
- attributes and indexing: `item.name`, `item["name"]`
- arithmetic, comparisons, and boolean logic
- pipelines and method pipes
- arrow lambdas: `x => x * 2`
- placeholder lambdas: `_`, `_1`, `_2`

For exact syntax, see the [Language Reference](reference.md).
