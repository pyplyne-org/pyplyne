---
title: purrr Examples
description: PyPlyne seq examples inspired by purrr documentation patterns.
---

# purrr Examples

PyPlyne's `seq` pipelines overlap with purrr's functional sequence style:
mapping over values, keeping values that match predicates, and using compact
callbacks for record-shaped data.

| Upstream pattern | Original docs | PyPlyne implementation | Run command |
| --- | --- | --- | --- |
| Map each element and return transformed values | [purrr `map()` examples](https://purrr.tidyverse.org/reference/map.html#examples) | `examples/parity/purrr_map_sequence.pyplyne` | `uv run pyplyne examples/parity/purrr_map_sequence.pyplyne` |
| Keep elements that match a predicate | [purrr `keep()` examples](https://purrr.tidyverse.org/reference/keep.html#examples) | `examples/parity/purrr_keep_records.pyplyne` | `uv run pyplyne examples/parity/purrr_keep_records.pyplyne` |

## Map Records To Values

This example mirrors purrr's "apply a function to every element" pattern with a
`seq` pipeline and PyPlyne's `_` placeholder.

```pyplyne title="examples/parity/purrr_map_sequence.pyplyne"
desserts = seq [
  {"name": "Sophia", "food": "banana bread"},
  {"name": "Eliott", "food": "pancakes"},
  {"name": "Karina", "food": "chocolate cake"},
]

messages = desserts
  |> map(_["food"] + " rocks!")

print(messages)
```

## Keep Records By Predicate

This example mirrors purrr's predicate-filtering family with PyPlyne's
record-aware `filter()` and field projection helpers.

```pyplyne title="examples/parity/purrr_keep_records.pyplyne"
samples = seq [
  {"id": 1, "values": [6, 7, 9, 5, 8], "active": True},
  {"id": 2, "values": [4, 5, 6, 5, 4], "active": False},
  {"id": 3, "values": [9, 8, 5, 2, 7], "active": True},
  {"id": 4, "values": [1, 2, 3, 4, 5], "active": False},
]

high_mean_samples = samples
  |> filter(sum(values) / len(values) > 6)
  |> keep_fields(id, values)

active_samples = samples
  |> filter(active == True)
  |> keep_fields(id)

print(high_mean_samples)
print(active_samples)
```

## Gaps To Track

PyPlyne does not currently implement purrr's typed `map_*()` variants, indexed
mapping, parallel mapping, list-column helpers, or error-handling wrappers. Add
new examples here as those concepts become relevant to PyPlyne's sequence
surface.
