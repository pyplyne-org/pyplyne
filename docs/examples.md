---
title: Examples
description: Runnable PyPlyne examples included in the repository.
---

# Examples

These examples are checked into the PyPlyne repository. If you installed PyPlyne
in your own project, copy the snippets you want to try into a local
`.pyplyne` file and run that file with `uv run pyplyne`.

If you cloned this repository, run the examples from the repository root:

## Filter And Map A Sequence

Start here for a minimal sequence pipeline: annotate a list with `seq`, use `_` in `filter` and `map`, and print the resulting list.

```bash
uv run pyplyne examples/list_pipeline.pyplyne
```

Shows:

- runnable sequence pipeline
- seq annotation
- _ placeholder expressions
- filter()
- map()
- print() result

```pyplyne title="examples/list_pipeline.pyplyne"
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)

print(result)
```

## Transform Rows In A Table

Start here for table data: declare inline rows with `df`, filter by column names, add a computed column, and project selected fields.

```bash
uv run pyplyne examples/tabular_pipeline.pyplyne
```

Shows:

- runnable table pipeline
- df annotation
- where()
- mutate()
- select()
- computed columns

```pyplyne title="examples/tabular_pipeline.pyplyne"
rows = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
]

large_sales = rows
  |> where(amount > 100)
  |> mutate(double=amount * 2)
  |> select(region, amount, double)

print(large_sales)
```

## Wrap A Polars DataFrame

Use this when Python code already creates a Polars DataFrame: import `polars as pl`, mark the object as `df`, then continue with PyPlyne table verbs.

```bash
uv run pyplyne examples/polars_constructor.pyplyne
```

Shows:

- Python imports
- Polars interop
- pl.DataFrame construction
- df annotation
- table verbs

```pyplyne title="examples/polars_constructor.pyplyne"
import polars as pl

sales = df pl.DataFrame([
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
])

large_sales = sales
  |> where(amount > 100)
  |> select(region, amount)

print(large_sales)
```

## Convert Tables To Rows And Back

Use this when a table workflow needs row-wise sequence logic: convert a filtered table to rows, map or edit records, then rebuild a table.

```bash
uv run pyplyne examples/shape_conversions.pyplyne
```

Shows:

- shape conversion
- to_rows()
- sequence map
- set_fields()
- to_table()
- arrange()

```pyplyne title="examples/shape_conversions.pyplyne"
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
]

labels = sales
  |> where(amount > 100)
  |> to_rows()
  |> map(_["region"])

reviewed = sales
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
  |> arrange(region)

print(labels)
print(reviewed)
```

## Edit Record Fields

Use this for JSON-like row dictionaries: derive new fields, remove debug-only fields, and keep the final shape explicit.

```bash
uv run pyplyne examples/record_fields.pyplyne
```

Shows:

- record dictionaries
- set_fields()
- drop_fields()
- keep_fields()
- field projection

```pyplyne title="examples/record_fields.pyplyne"
rows = seq [
  {"region": "north", "amount": 120, "discount": 10, "debug": "a"},
  {"region": "south", "amount": 80, "discount": 5, "debug": "b"},
  {"region": "north", "amount": 220, "discount": 20, "debug": "c"},
]

with_fields = rows
  |> set_fields(
    net=amount - discount,
    reviewed=amount > 100,
    label=region + "-" + str(amount),
  )

without_debug = with_fields
  |> drop_fields(debug)

projected = without_debug
  |> keep_fields(region, amount, net, reviewed, label)

print(with_fields)
print(without_debug)
print(projected)
```

## Run The Full Language Tour

Use this as an end-to-end smoke test: it combines imports, sequence and table verbs, grouped summaries, deferred pipelines, shape conversion, and CSV output.

```bash
uv run pyplyne examples/full_language_tour.pyplyne
```

Shows:

- end-to-end tour
- imports
- sequence verbs
- table verbs
- group_by() and summarize()
- defer pipeline
- write_csv() output

```pyplyne title="examples/full_language_tour.pyplyne"
from pathlib import Path

numbers = seq [1, 2, 3, 4, 5, 6]

sequence_total = numbers
  |> filter(_ > 2)
  |> map(x => x * 10)
  |> reduce(_1 + _2)

rows = df [
  {"region": "north", "amount": 120, "discount": 10},
  {"region": "south", "amount": 80, "discount": 5},
  {"region": "north", "amount": 220, "discount": 20},
  {"region": "south", "amount": 180, "discount": 15},
]

summary = rows
  |> where(amount > 100)
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

plan = defer rows
  |> where(amount > 100)
  |> select(region, amount)

summary_rows = summary |> to_rows()
summary_table = summary_rows |> to_table()
reviewed_sales = rows
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
  |> arrange(region)

output_path = Path("examples/full_language_tour_output.csv")
summary_table |> write_csv(str(output_path))

print(sequence_total)
print(summary)
print(plan)
print(summary_rows)
print(reviewed_sales)
```

## Generated Output

The full tour writes `examples/full_language_tour_output.csv`. The generated
file is ignored by Git.

## Choosing An Example

| Goal | Example |
| --- | --- |
| Filter And Map A Sequence | `examples/list_pipeline.pyplyne` |
| Transform Rows In A Table | `examples/tabular_pipeline.pyplyne` |
| Wrap A Polars DataFrame | `examples/polars_constructor.pyplyne` |
| Convert Tables To Rows And Back | `examples/shape_conversions.pyplyne` |
| Edit Record Fields | `examples/record_fields.pyplyne` |
| Run The Full Language Tour | `examples/full_language_tour.pyplyne` |

:::note Source-backed examples

This page is generated from `site/data/example-catalog.json` and the actual
files in `examples/`. Update the runnable example file first, then regenerate
this page with `npm run docs:examples` from `site/`.

:::
