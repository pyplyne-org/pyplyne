# Examples

Run examples from the repository root. If this is your first command in a fresh
checkout, install the development environment first:

```bash
uv sync --extra dev
```

Then run any example with `uv run pyplyne`:

## Basics

```bash
uv run pyplyne examples/list_pipeline.pyplyne
```

Shows a `seq` annotation plus `filter` and `map`.
Expected output: `[20, 40, 60]`.

```bash
uv run pyplyne examples/tabular_pipeline.pyplyne
```

Shows a `df` annotation plus Polars-backed `where`, `mutate`, and `select`.
Expected output is a Polars table for the north rows over 100.

## Table Construction

```bash
uv run pyplyne examples/polars_constructor.pyplyne
```

Imports Polars directly and annotates a `pl.DataFrame` as `df`.
Expected output is a Polars table for the selected north rows.

## Shape Conversion

```bash
uv run pyplyne examples/shape_conversions.pyplyne
```

Moves between `df` and `seq` with `to_rows()` and `to_table()`.
Expected output includes `["north", "north"]` and a reviewed Polars table.

```bash
uv run pyplyne examples/record_fields.pyplyne
```

Shows `set_fields`, `drop_fields`, and `keep_fields` for manipulating
sequences of row dictionaries.
Expected output shows the fields added, the `debug` field removed, and the final
projection.

## Full Tour

```bash
uv run pyplyne examples/full_language_tour.pyplyne
```

Exercises imports, sequence verbs, table verbs, grouped summaries, `defer`,
shape conversion, and CSV output.

The full tour writes `examples/full_language_tour_output.csv`; tests remove it
after running.
