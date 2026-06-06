---
title: Language Reference
description: Compact reference for PyPlyne syntax, shapes, verbs, files, and imports.
---

# Language Reference

This is a lookup reference for PyPlyne syntax, shapes, verbs, and expression
forms. For a learning path, use the [Language Guide](language-guide.md).

## Quick Index

| Need | Use |
| --- | --- |
| Mark Python iterable data | `name = seq expression` |
| Mark table-shaped data | `name = df expression` |
| Pipe to a function | `value |> function(args...)` |
| Pipe to a method | `value |> .method(args...)` |
| Sequence transform | `map`, `filter`, `reduce` |
| Record field transform | `set_fields`, `drop_fields`, `keep_fields` |
| Table transform | `where`, `mutate`, `select`, `group_by`, `summarize`, `arrange` |
| Table/sequence boundary | `to_rows()`, `to_table()` |
| Keep a lazy Polars plan | `defer expression` |

## Statements

Each statement ends at a newline. Blank lines and `#` comments are ignored.

| Form | Syntax | Notes |
| --- | --- | --- |
| Expression | `expression` | Evaluates the expression. |
| Assignment | `name = expression` | Stores the evaluated result. |
| Import | `import package` | Supports comma-separated imports and `as` aliases. |
| From import | `from module import name` | Supports comma-separated names and `as` aliases. |

```pyplyne
import math as m
from pathlib import Path

answer = m.sqrt(81)
Path("data.csv").suffix
```

## Shapes

Shapes are pipeline contracts, not Python type annotations. They tell PyPlyne
which verb family may run at each pipeline step, and they normalize or validate
values at runtime.

| Shape | Runtime data | Valid verb family |
| --- | --- | --- |
| `seq` | Python iterables, especially JSON-like records/lists | Sequence verbs and record field verbs |
| `df` | Polars-backed table data | Table verbs |
| scalar | Any non-shaped value | No shape-specific verbs |

Shape annotations go on the right-hand side:

```pyplyne
numbers = seq [1, 2, 3]
sales = df read_csv("sales.csv")
```

`df [...]` turns row dictionaries into a Polars DataFrame. `seq ...` validates
that the value is iterable and not a single mapping.

The assigned name records the final shape of the whole expression:

```pyplyne
rows = sales |> to_rows()        # rows is seq-shaped
total = numbers |> reduce(_1 + _2)  # total is scalar
```

If a pipeline starts from an unshaped expression, seed the shape at the source:

```pyplyne
result = seq load_values() |> map(_ * 2)
```

## Pipeline Operator

`|>` threads the value on the left into the target on the right.

| Target | Syntax | Compiles as |
| --- | --- | --- |
| Function call | `value |> f(a, b=1)` | `f(value, a, b=1)` |
| Bare function name | `value |> collect` | `collect(value)` |
| Method call | `value |> .upper()` | `value.upper()` |

Method pipes and unknown/custom pipeline functions do not change PyPlyne's shape
tracking. PyPlyne assumes the current shape is preserved unless a known verb such
as `to_rows()` or `to_table()` changes it. If custom Python code changes shape,
start the next pipeline with an explicit `seq` or `df` boundary.

Pipelines may span lines around `|>`:

```pyplyne
result = numbers
  |> filter(_ > 1)
  |> map(_ * 10)
```

## Expressions

PyPlyne expressions are a small Python-like expression surface.

| Category | Supported forms |
| --- | --- |
| Literals | strings, numbers, lists, tuples, dictionaries, `True`, `False`, `None` |
| Names | identifiers, dotted attributes, imports |
| Calls | positional arguments, keyword arguments |
| Access | `.attribute`, `[index]` |
| Arithmetic | `+`, `-`, `*`, `/`, `//`, `%`, unary `+`, unary `-` |
| Comparisons | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Boolean logic | `and`, `or`, `not` |
| Lambdas | `x => expression`, `(x, y) => expression`, `fn x: expression` |
| Pipelines | `expression |> target` |

Not part of the current expression grammar: comprehensions, slices, `if`
expressions, assignment expressions, `in`, `is`, bitwise operators, exponent
operator `**`, star arguments, relative imports, and `import *`.

Chained comparisons are accepted in scalar Python-style expressions, but avoid
them inside table verbs. Use `amount > 100 and amount < 200` instead of
`100 < amount < 200` so PyPlyne can lower each comparison to Polars expressions.

## Lambdas And Placeholders

Sequence callback arguments can be explicit lambdas or placeholder expressions.

| Form | Arity | Example |
| --- | --- | --- |
| `_` | One argument | `map(_ * 2)` |
| `_1`, `_2`, ... | Numbered arguments | `reduce(_1 + _2)` |
| `name => expression` | One named argument | `map(x => x * 2)` |
| `(a, b) => expression` | Multiple named arguments | `reduce((total, x) => total + x)` |
| `fn name: expression` | Legacy named lambda | `map(fn x: x * 2)` |

Placeholder rules:

- `_` cannot be mixed with numbered placeholders in the same callback.
- Numbered placeholders must start at `_1` and be consecutive.
- Placeholder rewriting applies to `map`, `filter`, and `reduce` callback
  arguments.

## Sequence Verbs

Sequence verbs require a known `seq` pipeline and operate on Python iterables.

Sequence verb contracts:

- **`map(expression)`** returns a `seq` list by evaluating the callback once per
  item.
- **`filter(expression)`** returns a `seq` list of items whose callback result is
  truthy.
- **`reduce(expression)`** returns a scalar by combining items with a
  two-argument callback.
- **`reduce(expression, initial)`** returns a scalar by combining items from an
  explicit initial value.

```pyplyne
numbers = seq [1, 2, 3, 4]
doubled = numbers |> map(_ * 2)
evens = numbers |> filter(_ % 2 == 0)
total = numbers |> reduce(_1 + _2)
total_from_zero = numbers |> reduce(_1 + _2, 0)
```

For row dictionaries, `filter(...)` also accepts bare field expressions:

```pyplyne
orders = seq [{"item": "pens", "qty": 2}]
restock = orders |> filter(qty > 1)
```

A single bare name is preserved as a direct predicate function:

```pyplyne
orders |> filter(is_priority)
```

## Record Field Verbs

Record field verbs require a known `seq` pipeline whose items are row
dictionaries.

Record field verb contracts:

- **`set_fields(name=expression, ...)`** returns a `seq` of new row dictionaries
  with added or replaced fields.
- **`drop_fields(field, ...)`** returns a `seq` of new row dictionaries without
  the named fields. Missing fields are ignored.
- **`keep_fields(field, ...)`** returns a `seq` of new row dictionaries
  containing only fields that exist on the source row.

Field names in `drop_fields(...)` and `keep_fields(...)` may be bare names or
strings. Keyword arguments are not accepted there.

Inside `filter(...)` row expressions and `set_fields(...)`, bare names are
rewritten to look up dictionary fields or object attributes on the current row:

```pyplyne
rows |> filter(amount > 100)
rows |> set_fields(net=amount - discount, label=region + "-" + str(amount))
```

Missing fields and attributes compare as falsy, so `filter(amount > 100)`
skips rows without `amount`. Arithmetic still requires present values, so
`set_fields(net=amount - discount)` errors if either field is missing.

Use explicit lambdas when the callback should control row access itself:

```pyplyne
rows |> set_fields(label=row => row["region"].upper())
```

For sequences of callable objects, use placeholders when you want to call the
current item:

```pyplyne
predicates |> filter(_(sample))
```

## Table Verbs

Table verbs require a known `df` pipeline. PyPlyne compiles bare identifiers
inside table verbs into Polars column expressions.

Table verb contracts:

- **`where(condition)`** keeps rows where the condition is true.
  Shape: `df`. Polars context: `filter`.
- **`mutate(name=expression, ...)`** adds or replaces columns while keeping
  existing columns.
  Shape: `df`. Polars context: `with_columns`.
- **`select(column, ...)`** projects columns or expressions.
  Shape: `df`. Polars context: `select`.
- **`group_by(column, ...)`** groups rows before `summarize`.
  Shape: `df` until materialized. Polars context: `group_by`.
- **`summarize(name=aggregation, ...)`** aggregates each group, or the whole
  table if ungrouped.
  Shape: `df`. Polars context: `agg` or `select`.
- **`arrange(column, ..., descending=False)`** sorts rows by one or more
  expressions.
  Shape: `df`. Polars context: `sort`.
- **`collect()`** materializes a lazy Polars plan when present.
  Shape: `df`. Polars context: `collect`.

Table expression rules:

- Bare names such as `amount` compile to column references.
- `and`, `or`, and `not` compile to Polars boolean expression operators.
- Keyword names in `mutate(...)` and `summarize(...)` become output column
  names.
- `group_by(...)` must be followed by `summarize(...)` before the pipeline is
  materialized or assigned as `df`.

PyPlyne tracks `group_by(...)` as a table pipeline for compilation, but the
runtime value is a grouped Polars object. Use `summarize(...)` immediately after
`group_by(...)`; other verbs after a deferred grouped object may fail in Polars
rather than with a PyPlyne-specific diagnostic.

```pyplyne
summary = sales
  |> where(amount > 100 and region != "test")
  |> mutate(net=amount - discount)
  |> group_by(region)
  |> summarize(total=sum(net), average=mean(net), rows=count())
  |> arrange(region)
```

## Aggregation Helpers

Aggregation helpers are recognized inside table expressions and map to Polars
aggregations when their arguments are column expressions.

| Helper | Result |
| --- | --- |
| `sum(column)` | Sum of values. |
| `mean(column)` | Mean of values. |
| `min(column)` | Smallest value. |
| `max(column)` | Largest value. |
| `count()` | Count rows. |
| `count(column)` | Count values in a column expression. |

Without `group_by(...)`, `summarize(...)` aggregates the whole table:

```pyplyne
overall = sales |> summarize(total=sum(amount), rows=count())
```

## Shape Conversion

Use conversions explicitly at shape boundaries.

| Verb | From | To | Runtime result |
| --- | --- | --- | --- |
| `to_rows()` | `df` | `seq` | List of row dictionaries. |
| `to_table()` | `seq` | `df` | Polars DataFrame. |

```pyplyne
reviewed = sales
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
```

## File Helpers

Read helpers create table-shaped values, so `df read_csv(...)` is usually
redundant. Write helpers preserve the current pipeline value so writes can be
chained.

Read helpers return `df` values:

- **`read_csv(path, option=value, ...)`** uses a `polars.scan_csv` lazy scan.
- **`read_json(path, option=value, ...)`** uses `polars.read_json`.
- **`read_parquet(path, option=value, ...)`** uses `polars.read_parquet`.
- **`read_excel(path, option=value, ...)`** uses `polars.read_excel`.

Write helpers preserve the current shape:

- **`write_csv(path, option=value, ...)`** uses a Polars CSV writer or Python
  `csv.DictWriter` for row dictionaries.
- **`write_json(path, option=value, ...)`** uses a Polars JSON writer or
  `json.dumps` for non-tables.
- **`write_parquet(path, option=value, ...)`** uses a Polars Parquet writer.
- **`write_excel(path, option=value, ...)`** uses a Polars Excel writer.

Excel support requires:

```bash
uv sync --extra excel
```

## Deferred Execution

PyPlyne materializes lazy Polars results at normal assignment and expression
boundaries. Prefix an expression with `defer` to keep its lazy plan. Avoid
adding `df` around a lazy plan you want to preserve, because `df` normalization
can collect lazy frames.

```pyplyne
plan = defer read_csv("sales.csv")
  |> where(amount > 100)
```

`defer` preserves the expression shape. It does not convert between `df` and
`seq`; use `to_rows()` and `to_table()` for shape conversion.

## Imports

Imports compile to native Python import AST nodes and use Python's import
system at runtime.

| Syntax | Example |
| --- | --- |
| `import dotted.name` | `import polars` |
| `import dotted.name as alias` | `import polars as pl` |
| `from dotted.name import name` | `from pathlib import Path` |
| `from dotted.name import name as alias` | `from math import sqrt as root` |

## Common Boundaries

Common boundary fixes:

- **`map requires a known seq pipeline`**
  Cause: source has no known shape.
  Fix: add `seq` at the source.
- **`where is a df verb, but the current pipeline is seq`**
  Cause: table verb after sequence data.
  Fix: use `to_table()` if the rows are table-shaped.
- **`map is a seq verb, but the current pipeline is df`**
  Cause: sequence verb after table data.
  Fix: use `to_rows()` first.
- **`group_by(...) must be followed by summarize(...)`**
  Cause: grouped table reached materialization.
  Fix: add `summarize(...)` before assignment/output.
- **`seq annotation expects iterable data, got mapping`**
  Cause: a single dictionary was annotated as `seq`.
  Fix: wrap it in a list for a row sequence.
- **`syntax error: shape annotations go on the right-hand side`**
  Cause: legacy left-hand shape declaration.
  Fix: use `name = seq ...` or `name = df ...`.
- **`df annotation expects table-shaped data`**
  Cause: `df` was applied to scalar or non-table data.
  Fix: use table-shaped values or convert records with `to_table()`.
- **`to_rows` or `to_table` wrong-shape errors**
  Cause: shape conversion was used from the wrong source shape.
  Fix: use `to_rows()` from `df`, and `to_table()` from `seq`.
- **Write helper requires a known shape**
  Cause: a write helper was called on an unshaped pipeline.
  Fix: start with `seq` or `df`, or assign a shaped name first.
