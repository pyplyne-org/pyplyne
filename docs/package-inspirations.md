---
title: Package Inspirations
description: PyPlyne examples inspired by existing data and functional pipeline packages.
---

# Package Inspirations

PyPlyne borrows proven ideas from existing pipeline ecosystems, especially
functional sequence tools and dataframe transformation libraries. These pages
collect small, runnable examples that mirror selected upstream documentation
patterns so PyPlyne can track functional parity over time.

These are not ports of the upstream packages. Each example is a deterministic
PyPlyne implementation with a link to the original documentation pattern it is
inspired by.

## Sections

| Package inspiration | PyPlyne shape | Examples |
| --- | --- | --- |
| [purrr](package-inspirations/purrr.md) | `seq` | Mapping values and keeping records by predicate |
| [dplyr](package-inspirations/dplyr.md) | `df` | Filtering, selecting, mutating, grouping, and summarizing tables |

## Run The Examples

Run any checked-in package inspiration example from the repository root:

```bash
uv run pyplyne examples/parity/purrr_map_sequence.pyplyne
uv run pyplyne examples/parity/purrr_keep_records.pyplyne
uv run pyplyne examples/parity/dplyr_filter_select_mutate.pyplyne
uv run pyplyne examples/parity/dplyr_group_summary.pyplyne
```

The tests also execute these files directly, so each page doubles as
documentation and a small parity checklist.

## Current Boundaries

The package inspiration examples stay inside PyPlyne's current language surface.
They deliberately avoid upstream features PyPlyne does not implement yet, such
as typed `map_*()` variants, tidyselect helpers, joins, slices, and bundled R
datasets.
