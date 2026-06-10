---
title: dplyr Examples
description: PyPlyne df examples inspired by dplyr documentation patterns.
---

# dplyr Examples

PyPlyne's `df` pipelines are Polars-backed and intentionally use dplyr-like
verbs for table workflows. These examples cover the current overlap:
`where`, `mutate`, `select`, `group_by`, `summarize`, and `arrange`.

| Upstream pattern | Original docs | PyPlyne implementation | Run command |
| --- | --- | --- | --- |
| Filter rows, select columns, and derive BMI | [dplyr overview examples](https://dplyr.tidyverse.org/#usage) and [intro filter example](https://dplyr.tidyverse.org/articles/dplyr.html#filter-rows-with-filter) | `examples/parity/dplyr_filter_select_mutate.pyplyne` | `uv run pyplyne examples/parity/dplyr_filter_select_mutate.pyplyne` |
| Group rows and summarize per group | [dplyr overview grouped summary](https://dplyr.tidyverse.org/#usage) | `examples/parity/dplyr_group_summary.pyplyne` | `uv run pyplyne examples/parity/dplyr_group_summary.pyplyne` |

## Filter, Select, And Mutate

This example mirrors common dplyr row filtering, column projection, and derived
column patterns against a small local `starwars`-style table.

```pyplyne title="examples/parity/dplyr_filter_select_mutate.pyplyne"
starwars = df [
  {"name": "Luke Skywalker", "height": 172, "mass": 77, "skin_color": "fair", "eye_color": "blue", "species": "Human"},
  {"name": "Leia Organa", "height": 150, "mass": 49, "skin_color": "light", "eye_color": "brown", "species": "Human"},
  {"name": "Biggs Darklighter", "height": 183, "mass": 84, "skin_color": "light", "eye_color": "brown", "species": "Human"},
  {"name": "C-3PO", "height": 167, "mass": 75, "skin_color": "gold", "eye_color": "yellow", "species": "Droid"},
  {"name": "R2-D2", "height": 96, "mass": 32, "skin_color": "white, blue", "eye_color": "red", "species": "Droid"},
]

light_brown_eyes = starwars
  |> where(skin_color == "light" and eye_color == "brown")
  |> select(name, skin_color, eye_color)

with_bmi = starwars
  |> mutate(bmi=mass / ((height / 100) * (height / 100)))
  |> select(name, height, mass, bmi)
  |> arrange(name)

print(light_brown_eyes.to_dicts())
print(with_bmi.to_dicts())
```

## Group And Summarize

This example mirrors grouped summary patterns using `group_by()` followed by
`summarize()`.

```pyplyne title="examples/parity/dplyr_group_summary.pyplyne"
starwars = df [
  {"name": "Luke Skywalker", "species": "Human", "mass": 77},
  {"name": "Leia Organa", "species": "Human", "mass": 49},
  {"name": "Biggs Darklighter", "species": "Human", "mass": 84},
  {"name": "C-3PO", "species": "Droid", "mass": 75},
  {"name": "R2-D2", "species": "Droid", "mass": 32},
  {"name": "Jar Jar Binks", "species": "Gungan", "mass": 66},
  {"name": "Roos Tarpals", "species": "Gungan", "mass": 82},
]

species_summary = starwars
  |> group_by(species)
  |> summarize(rows=count(), average_mass=mean(mass))
  |> where(rows > 1 and average_mass > 50)
  |> arrange(species)

print(species_summary.to_dicts())
```

## Gaps To Track

PyPlyne does not currently implement dplyr's tidyselect helpers such as
`starts_with()` and `ends_with()`, `desc()`, joins, row slicing, window
functions, or bundled datasets. Add new examples here as those table surfaces
land.
