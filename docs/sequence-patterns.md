---
title: Sequence Patterns
description: Use PyPlyne seq pipelines with scalars, records, objects, functions, and mixed Python values.
---

# Sequence Patterns

`seq` pipelines run over non-string, non-mapping Python iterables. A sequence
can contain plain values, row dictionaries, objects, functions, or other Python
values. Polars tables annotated as `seq` are converted to row dictionaries. The
main rule is: use the shorthand that matches what each item is.

## Plain Values

For numbers, strings, and other scalar values, use placeholders or lambdas:

```pyplyne
values = seq [1, 2, 3, 4]

result = values
  |> filter(_ > 1)
  |> map(_ * 10)
```

`_` means the current item. Use `_1`, `_2`, and so on for callbacks that receive
more than one value:

```pyplyne
total = values |> reduce(_1 + _2)
```

## Row Dictionaries

For JSON-like records, `filter(...)` and `set_fields(...)` can read dictionary
fields with bare names:

```pyplyne
orders = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens", "qty": 2},
  {"item": "paper"},
]

restock = orders
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
```

Rows without `qty` are skipped by the filter. Missing fields are
boolean-false; `item == "pens"` is `False` when `item` is absent, while
`item != "pens"` is `True` for rows without `item`.

Arithmetic still requires present values. This errors if a row is missing `qty` or
`price`:

```pyplyne
orders |> set_fields(total = qty * price)
```

That distinction keeps filtering forgiving while still surfacing missing data in
calculations.

### Sparse JSON Rows

When JSON records do not all have the same keys, use comparisons to make the
missing-field behavior explicit:

```pyplyne
events = seq [
  {"id": 1, "status": "open"},
  {"id": 2},
  {"id": 3, "status": "closed"},
]

open_events = events |> filter(status == "open")
not_closed_events = events |> filter(status != "closed")
with_flags = events |> set_fields(is_open = status == "open")
```

`open_events` contains only rows whose `status` exists and equals `"open"`.
`not_closed_events` also keeps rows without `status`, because missing fields do
not equal `"closed"`. `with_flags` sets `is_open` to `False` on rows where
`status` is absent.

The same rule applies when a field name is misspelled or the upstream JSON
schema changes:

```pyplyne
typoed = events |> filter(stauts == "open")
both_missing = events |> filter(nonsense1 == nonsense2)
```

`stauts` is treated as a missing field on every row. The pipeline still runs,
but the result is wrong for a required-field workflow. If both sides are
misspelled or renamed, `nonsense1 == nonsense2` still matches no rows, while
`nonsense1 != nonsense2` matches rows where both fields are absent. When a field
must exist, validate the input shape first or use explicit row access in a
Python helper that raises on missing keys.

## Python Objects

The same bare-name shorthand works with object attributes in `filter(...)`:

```pyplyne
priority = seq orders
  |> filter(qty > 1)
```

If `orders` contains Python objects with a `.qty` attribute, PyPlyne reads that
attribute. Objects without the attribute do not match comparison filters.
Record field verbs such as `set_fields(...)`, `drop_fields(...)`, and
`keep_fields(...)` require row dictionaries, not arbitrary objects.

Use explicit lambdas when the object API is richer than simple attributes:

```pyplyne
priority = seq orders
  |> filter(order => order.is_priority())
  |> map(order => order.to_dict())
```

## Functions And Callables

Functions are ordinary Python objects, so you can filter by attributes:

```pyplyne
chosen = seq checks
  |> filter(__name__ == "is_priority")
```

When you want to call the current item, use `_`:

```pyplyne
passing = seq checks
  |> filter(_("sample input"))
```

If you have a named predicate function and want to use it directly, pass the
bare function name:

```pyplyne
orders |> filter(is_priority)
```

PyPlyne preserves a single bare name in `filter(...)` as a predicate function.
Expressions such as `qty > 1` are treated as row-field or object-attribute
predicates.

## When To Use Which Form

- Use `_` for the current item: `filter(_ > 10)`, `map(_["item"])`,
  `filter(_(sample))`.
- Use bare fields or attributes in record/object filters: `filter(qty > 1)`.
- Use bare fields in dictionary record updates: `set_fields(net = amount - discount)`.
- Use `keep_fields(...)` and `drop_fields(...)` for dictionary-shaped rows.
- Use explicit lambdas when you need method calls, custom names, or richer
  object behavior.

A single bare name in `filter(...)` is treated as a predicate function, not as a
field truthiness check:

```pyplyne
orders |> filter(is_priority)
orders |> filter(active == True)
orders |> filter(_["active"])
```

`map(...)` does not infer bare fields. Use a placeholder or lambda there:

```pyplyne
items = orders |> map(_["item"])
items = orders |> map(order => order["item"])
```

## Crossing To Tables

Use `to_table()` when your sequence is a list of row dictionaries and you want
Polars-backed table verbs:

```pyplyne
summary = seq orders
  |> filter(qty > 1)
  |> set_fields(buy = item == "pens")
  |> to_table()
  |> group_by(buy)
  |> summarize(rows = count())
```

Use `to_rows()` to move from a table into record-by-record sequence work.
