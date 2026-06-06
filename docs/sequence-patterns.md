---
title: Sequence Patterns
description: Use PyPlyne seq pipelines with scalars, records, objects, functions, and mixed Python values.
---

# Sequence Patterns

`seq` pipelines run over Python iterables. A sequence can contain plain values,
row dictionaries, objects, functions, or other Python values. The main rule is:
use the shorthand that matches what each item is.

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

For JSON-like records, `filter(...)` and `set_fields(...)` can read fields with
bare names:

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

Rows without `qty` are skipped by the filter. Missing fields compare as falsy,
so `item == "pens"` becomes `False` when `item` is absent.

Arithmetic still requires present values. This errors if a row is missing `qty` or
`price`:

```pyplyne
orders |> set_fields(total = qty * price)
```

That distinction keeps filtering forgiving while still surfacing missing data in
calculations.

## Python Objects

The same bare-name shorthand works with object attributes:

```pyplyne
priority = seq orders
  |> filter(qty > 1)
```

If `orders` contains Python objects with a `.qty` attribute, PyPlyne reads that
attribute. Objects without the attribute do not match comparison filters.

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
- Use bare fields in record/object filters: `filter(qty > 1)`.
- Use bare fields in record updates: `set_fields(net = amount - discount)`.
- Use `keep_fields(...)` and `drop_fields(...)` for dictionary-shaped rows.
- Use explicit lambdas when you need method calls, custom names, or richer
  object behavior.

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
