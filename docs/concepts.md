---
title: Core Concepts
description: The mental model for PyPlyne pipelines, shapes, execution, and Python interop.
---

# Core Concepts

PyPlyne brings clean functional pipes directly to Python. It compiles to Python
AST, runs in a normal Python environment, and is built around four ideas:

- pipelines describe data flow from left to right
- shapes choose the verb family for each step
- table expressions are Polars expressions
- Python objects stay available at the boundaries

## Pipelines Read Left To Right

`|>` sends the value on the left into the call on the right:

```pyplyne
result = numbers
  |> filter(_ > 1)
  |> map(_ * 10)
```

Conceptually:

```python
[item * 10 for item in numbers if item > 1]
```

PyPlyne writes that flow in the order you think about it.

Each step receives the current value and returns the next value. Most verbs
preserve the same shape, while terminal verbs such as `reduce(...)` can return
a scalar.

## Shapes Are The Pipeline Contract

PyPlyne distinguishes two pipeline shapes:

| Shape | Mental model | Main verbs |
| --- | --- | --- |
| `seq` | Non-string, non-mapping Python iterables; Polars tables become row dictionaries | `map`, `filter`, `reduce`, `set_fields`, `drop_fields`, `keep_fields` |
| `df` | a table of rows and columns | `where`, `mutate`, `select`, `group_by`, `summarize`, `arrange` |

Shape annotations go on the right-hand side:

```pyplyne
orders = seq [{"item": "coffee", "qty": 3}]
sales = df read_csv("sales.csv")
```

A shape is not a Python type annotation. It tells PyPlyne how to compile the
pipeline that follows, and it normalizes or validates values at runtime.
`df [...]` becomes a Polars DataFrame; `seq ...` checks that the value is a
non-string, non-mapping iterable rather than a scalar or single record. Polars
tables annotated as `seq` are converted to row dictionaries. If a variable is
already known to be `seq` or `df`, later pipelines can start from that variable
without repeating the annotation:

```pyplyne
large_sales = sales |> where(amount > 100)
```

:::tip
If a pipeline starts from an arbitrary Python expression or a custom function,
annotate the source with `seq` or `df` so PyPlyne knows which verb family applies.
:::

## Sequence Pipelines Transform Items

Use `seq` when each step should work item by item. The value can be a list,
tuple, generator, API response, or another non-string, non-mapping Python
iterable.

```pyplyne
values = seq [1, 2, 3, 4]

doubled = values |> map(_ * 2)
evens = values |> filter(_ % 2 == 0)
total = values |> reduce(_1 + _2)
```

Inside sequence callbacks, `_` is the current item. Numbered placeholders such
as `_1` and `_2` are available for callbacks that receive more than one value.

Sequences of dictionaries are useful for JSON-like records:

```pyplyne
orders = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens", "qty": 2},
]

restock = orders
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
```

Inside record `filter(...)` expressions, bare names can read dictionary fields
or object attributes on the current item. Inside `set_fields(...)`, bare names
read fields from row dictionaries, and the input rows must be dictionaries:

```pyplyne
rows |> filter(amount > 100)
rows |> set_fields(net = amount - discount)
```

Think of sequence verbs like compact Python loops: `map` transforms each item,
`filter` keeps some items, and `reduce` collapses the sequence to one result.

## Table Pipelines Transform Columns

Inside table verbs, bare names are column references:

```pyplyne
summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total = sum(amount), rows = count())
```

`amount` and `region` are not Python variables there. They are compiled into
Polars expressions and executed by the Polars backend.

Table verbs describe the part of the table they change:

- `where` filters rows
- `mutate` adds or replaces columns
- `select` chooses columns
- `group_by` changes the grouping context
- `summarize` reduces each group to summary columns
- `arrange` sorts rows

This is the same idea Polars uses for expression contexts: an expression does
not do work by itself. It runs when placed in a context such as filtering,
selecting, mutating, or aggregating.

## Execution Runs By Default

PyPlyne materializes table pipelines by default at assignment and expression
boundaries. When you run a script, the pipeline runs and you get a concrete
result.

Use `defer` only when you want to keep a lazy Polars plan:

```pyplyne
plan = defer sales
  |> where(amount > 100)
  |> select(region, amount)
```

Avoid adding `df` around a lazy plan you want to preserve, because `df`
normalization can collect lazy frames.

`collect()` remains available for lazy Polars plans, but it is not the normal
boundary between PyPlyne and results.

## Shape Boundaries Are Explicit

Use explicit helpers to cross between table and sequence workflows:

```pyplyne
rows = sales |> to_rows()
table = rows |> to_table()
```

Conversions can happen inside one pipeline:

```pyplyne
reviewed = sales
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
  |> arrange(region)
```

Use table verbs while you want Polars column behavior. Convert to rows when you
want Python item behavior. Convert back when you want table behavior again.

## Python Is The Host Language

Imports compile to native Python import nodes:

```pyplyne
from pathlib import Path
import polars as pl
```

Python values can enter a PyPlyne pipeline:

```pyplyne
from pathlib import Path
from scoring import score_order

root = Path(".")
ranked = seq orders |> map(score_order(_))
```

The important boundary is expression meaning:

- sequence callbacks use normal Python semantics
- table verb expressions use column semantics
- arbitrary Python calls are best made before a table pipeline, after it, or on
  rows after `to_rows()`

You can also run PyPlyne from Python:

```python
from pyplyne import PyPlyneSession

orders = [
    {"item": "coffee", "qty": 3},
    {"item": "pens", "qty": 2},
]
session = PyPlyneSession({"orders": orders})
session.run("""
restock = seq orders
  |> filter(qty > 1)
""")
```

The session environment can hold Python objects, imported functions, Polars
tables, and intermediate PyPlyne results.

## Interactive Sessions Keep Context

The REPL and session server keep variables, imports, data, and known shapes
alive between snippets:

```pyplyne
pyplyne> numbers = seq [1, 2, 3]
pyplyne> numbers |> map(_ * 10)
[10, 20, 30]
pyplyne> _ |> filter(_ > 10)
[20, 30]
```

In an interactive session, `_` has two roles. At the start of a pipeline it is
the previous expression result. Inside sequence callbacks it is the current
item. If the previous result is scalar, PyPlyne clears the stored shape so later
shape-specific verbs do not accidentally use stale context.
