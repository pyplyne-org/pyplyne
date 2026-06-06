---
title: Troubleshooting
description: Common PyPlyne errors and how to fix them.
---

# Troubleshooting

PyPlyne diagnostics identify the phase where the problem happened. Start there,
then match the error symptom.

| Phase | Meaning | First thing to check |
| --- | --- | --- |
| `parse` | The source did not match the grammar. | Syntax near the caret, unsupported expression forms, or shape annotations on the wrong side. |
| `compile` | The source parsed, but the compiler rejected the pipeline semantics. | Shape contracts, verb families, placeholders, and pipeline source annotations. |
| `runtime` | Python or Polars raised while executing the compiled code. | Exception type, data shape, column names, files, dependencies, and Python tracebacks. |

## First Pass Triage

Use text diagnostics when reading failures by hand:

```bash
uv run pyplyne send --expr 'rows |> where(amount > 0)'
```

Use JSON when another tool, editor, or test needs structured fields:

```bash
uv run pyplyne send --expr 'rows |> where(amount > 0)' --json
```

The JSON response includes `ok`, `phase`, `error`, `traceback`, `shapes`, and a
`diagnostic` object with fields such as `error_type`, `message`, `line`,
`column`, `source`, `caret`, `hint`, and `display`.

Failed server requests return a non-2xx HTTP status, but the response body still
contains the useful JSON diagnostic. Clients and tests should read the body even
when their HTTP library raises an error.

Good debugging loop:

1. Read `phase` and `error_type` first.
2. Use `source`, `line`, `column`, and `caret` to identify the smallest failing
   expression.
3. Check `hint` before reading the full traceback.
4. Use `shapes` to confirm whether each name is `seq`, `df`, or scalar.
5. Fix one contract at a time and rerun the smallest expression.

For piped or generated source, pass a stable virtual filename so diagnostics
point to something recognizable:

```bash
printf 'numbers = seq [1, 2, 3\n' \
  | uv run pyplyne send --json --filename scratch.pyplyne
```

## Parse Errors

Parse errors mean PyPlyne could not read the source as valid PyPlyne syntax. Fix the
source form before looking for type, data, or Polars issues.

Common parse symptoms:

- **`syntax error` near the end of a line**
  Cause: missing `]`, `)`, `}`, quote, or newline.
  Fix: balance delimiters and rerun the smallest statement.
- **`shape annotations go on the right-hand side`**
  Cause: a shape was written before the name.
  Fix: write `name = seq expression` or `name = df expression`.
- **The caret is on Python syntax that works outside PyPlyne**
  Cause: the expression uses syntax not in PyPlyne's current grammar, such as
  comprehensions, slices, `if` expressions, `in`, `is`, `**`, star arguments,
  or `import *`.
  Fix: move that logic into an imported Python helper, or rewrite with
  supported expressions and verbs.

### Shape Annotation On The Wrong Side

Use shape annotations on the right-hand side:

```pyplyne
sales = df read_csv("sales.csv")
```

Not:

```pyplyne
df sales = read_csv("sales.csv")
```

## Compile Errors

Compile errors mean the syntax is readable, but the pipeline contracts do not
make sense yet.

Common compile symptoms:

- **`where is a df verb, but the current pipeline is seq`**
  Cause: a table verb is running on sequence-shaped data.
  Fix: start with `df`, convert with `to_table()`, or use the matching sequence
  verb.
- **`filter is a seq verb, but the current pipeline is df`**
  Cause: a sequence verb is running on table-shaped data.
  Fix: start with `seq`, convert with `to_rows()`, or use the matching table
  verb.
- **`requires a known seq pipeline` or `requires a known df pipeline`**
  Cause: a pipeline starts from an arbitrary expression whose shape is unknown.
  Fix: seed the source with `seq` or `df`.
- **`cannot mix _ with numbered placeholders`**
  Cause: a callback uses `_` and `_1`/`_2` together.
  Fix: use only `_` for one argument, or only numbered placeholders.
- **`numbered placeholders must start at _1 and be consecutive`**
  Cause: a callback skips placeholder numbers.
  Fix: use `_1`, `_2`, ... without gaps.

### Wrong Verb Family

`where` is a table verb. `filter` is a sequence verb.

```pyplyne
rows = seq [{"amount": 120}]
rows |> filter(amount > 100)
```

```pyplyne
rows = df [{"amount": 120}]
rows |> where(amount > 100)
```

If you need to cross shapes, use `to_rows()` or `to_table()`:

```pyplyne
rows = df [{"amount": 120}]
high_value_rows = rows
  |> to_rows()
  |> filter(amount > 100)
```

### Missing Shape For A Pipeline Source

When a pipeline starts from an arbitrary expression, annotate it:

```pyplyne
total = seq load_values()
  |> reduce(_1 + _2)
```

This tells PyPlyne which verb family should apply.

## Runtime Errors

Runtime errors come from executing generated Python. The last line of the error
usually gives the exception type and message; the traceback and PyPlyne diagnostic
show the context that led there.

Common runtime symptoms:

- **`TypeError: seq annotation expects iterable data`**
  Cause: `seq` was applied to a scalar or non-iterable value.
  Fix: use iterable data, or wrap one item in a list.
- **`TypeError: df annotation expects table-shaped data`**
  Cause: `df` was applied to a scalar or other non-table value.
  Fix: use dictionaries, row lists, DataFrames, LazyFrames, or file/table reads.
- **`ColumnNotFoundError`**
  Cause: a Polars table expression referenced a missing column.
  Fix: check spelling, inspect the columns before this step, or move
  `select(...)` until after all needed columns are used.
- **`SchemaError`, `ShapeError`, `InvalidOperationError`, or `ComputeError`**
  Cause: Polars found a schema, dtype, shape, or computation mismatch.
  Fix: confirm the input schema, cast or parse values before the operation, and
  materialize lazy boundaries with `collect()` when needed.
- **`FileNotFoundError`**
  Cause: a file read is using the wrong path or working directory.
  Fix: run from the expected project root, use an absolute path, or check the
  path before `read_csv`, `read_json`, `read_parquet`, or `read_excel`.
- **`NameError: name ... is not defined`**
  Cause: a function, helper, or import is missing from the session.
  Fix: import the module, define the helper, or use a supported PyPlyne verb.
- **`group_by(...) must be followed by summarize`**
  Cause: a grouped table state was assigned or materialized too early.
  Fix: add `summarize(...)`, or remove `group_by(...)` before assignment.
- **Excel import or engine errors**
  Cause: Excel support was not installed.
  Fix: install the optional Excel dependencies.

### `seq` Got A Scalar Or Mapping

`seq` expects iterable data. Wrap a single record in a list:

```pyplyne
row = seq [{"item": "coffee", "qty": 3}]
```

If the data is table-shaped, use `df` instead:

```pyplyne
row = df {"item": "coffee", "qty": 3}
```

### Missing Column In A Table Verb

Bare names inside table verbs are Polars column references:

```pyplyne
sales = df [{"amount": 120}]
sales |> where(missing > 0)
```

If this raises `ColumnNotFoundError`, inspect the available columns and use the
actual column name:

```pyplyne
sales |> where(amount > 0)
```

If a column is created in `mutate(...)`, keep the `mutate(...)` before any
`where(...)`, `select(...)`, `group_by(...)`, or `summarize(...)` step that uses
the new column.

### `group_by` Without `summarize`

`group_by(...)` creates a grouped table state. Follow it with `summarize(...)`
before assignment:

```pyplyne
summary = sales
  |> group_by(region)
  |> summarize(total = sum(amount))
```

### Excel Helpers Are Missing Dependencies

Excel support is optional:

```bash
uv sync --extra excel
```

## Interactive Sessions

Persistent sessions keep variables, imports, shapes, and `_` between requests.
That is useful, but stale state can make a new snippet look broken.

Use the REPL shape commands:

```text
:vars
:shapes
```

With the session server, request JSON diagnostics:

```bash
uv run pyplyne send --expr 'rows |> where(amount > 0)' --json
```

Fix patterns for session confusion:

- **A name exists but has the wrong shape:** reassign it with the intended `seq`
  or `df` annotation, or start a fresh session.
- **A previous failed run left later code confusing:** check `shapes`; parse and
  compile failures do not execute the snippet, but runtime failures can leave
  earlier successful statements from the same snippet in `env`.
- **Diagnostics refer to a generic session label:** use `--filename` for piped
  or expression source.
- **Text output hides the full stack trace:** use `--json` or
  `run(..., raise_on_error=False)` and inspect `traceback`.

## Python API Diagnostics

By default, `PyPlyneSession.run(...)` raises errors. For applications, tests, and
agents, capture the result and inspect the raw Python result fields:

```python
from pyplyne import PyPlyneSession

session = PyPlyneSession()
result = session.run("bad = seq 42\n", raise_on_error=False)

if not result.ok:
    print(result.phase)
    print(type(result.error).__name__, result.error)
    print(result.traceback)
    print(result.shapes)
```

The Python API result exposes `phase`, `error`, `traceback`, `stdout`,
`stderr`, `result`, and `shapes`. The HTTP JSON response adds the formatted
`diagnostic` object with `error_type`, `line`, `column`, `caret`, `hint`, and
`display`.

When turning a fix into a regression test, assert the specific failure mode
instead of only checking that "something failed":

```python
result = session.run("nonsense = seq 42\n", raise_on_error=False)

assert not result.ok
assert result.phase == "runtime"
assert type(result.error).__name__ == "TypeError"
assert "seq annotation expects iterable data" in str(result.error)
```
