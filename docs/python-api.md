---
title: Python API
description: Run PyPlyne from Python with PyPlyneSession, parse_source, and compile_ast.
---

# Python API

Use the Python API when you want to run PyPlyne inside another application,
notebook, agent, or test suite. Common imports are:

```python
from pyplyne import run, run_file, PyPlyneSession
```

Use `run(...)` when you want a single isolated execution. Use
`PyPlyneSession` when you want variables, imports, shapes, and the last result
to persist across multiple snippets. The parser and compiler helpers are
available for tools that need direct access to the generated Python AST. See
the [Generated Python API Reference](generated-python-api-reference) for the
full public export list and exact signatures.

## Choose An API

| Task | Use |
| --- | --- |
| Run PyPlyne source once with no persistent state | `run(...)` |
| Run a `.pyplyne` file once with no persistent state | `run_file(...)` |
| Run PyPlyne snippets repeatedly with shared state | `PyPlyneSession.run(...)` |
| Seed a run with Python objects | `PyPlyneSession({...})` |
| Run a `.pyplyne` file in the same environment | `PyPlyneSession.load_file(...)` |
| Retrieve a named output as a Python object | `session.get(...)` |
| Retrieve a named table as a Polars DataFrame | `session.get_df(...)` |
| Retrieve a named sequence as a Python list/tuple | `session.get_seq(...)` |
| Inspect captured output/errors from a run | `PyPlyneExecutionResult` |
| Capture diagnostics instead of raising | `run(..., raise_on_error=False)` |
| Build editor, lint, or compiler tooling | `parse_source(...)` and `compile_ast(...)` |

## Run Source Once

For ordinary Python embedding, start here. Pass any Python objects the PyPlyne
source needs through `context`, end the source with the value you want back, and
read it from `result.result`.

```python
import polars as pl
from pyplyne import run

sales = pl.DataFrame([
    {"region": "north", "amount": 120},
    {"region": "south", "amount": 80},
])

result = run("""
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""", context={"sales": sales})

summary = result.result
assert isinstance(summary, pl.DataFrame)
```

Each `run(...)` call is isolated. It does not remember names or shapes from a
previous call. Use `PyPlyneSession` when you want that stateful behavior.

## Run Source In A Session

```python
from pyplyne import PyPlyneSession

session = PyPlyneSession({
    "orders": [
        {"item": "coffee", "qty": 3},
        {"item": "pens", "qty": 2},
    ],
})

result = session.run("""
restock = seq orders
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
""")

assert result.ok
print(session.get_seq("restock"))
```

`PyPlyneSession` keeps state between runs:

- a Python globals dictionary
- runtime helper functions
- loaded values
- imports
- known `seq`/`df` shape information
- the last expression result as `_`

That makes a session a good fit for REPLs, server handlers, notebooks, and
tests that build up fixtures once and then run several PyPlyne snippets.

## Inspect Results

`run(...)` returns a `PyPlyneExecutionResult`. When the final statement is an
expression, the value is also available as `result.result` and `session.env["_"]`.

```python
session = PyPlyneSession({"numbers": [1, 2, 3]})

result = session.run("""
seq numbers
  |> map(_ * 10)
""")

assert result.ok
assert result.result == [10, 20, 30]
assert session.env["_"] == [10, 20, 30]
print(result.stdout)
print(result.shapes)
```

Pass a `filename` when the source comes from a user file, notebook cell, or
editor buffer. PyPlyne uses it in tracebacks and diagnostics.

```python
session.run(source_text, filename="orders.pyplyne")
```

When constructing source strings yourself, include the same trailing newline a
`.pyplyne` file would have.

## Execution Options

`run(...)`, `run_file(...)`, and `PyPlyneSession.run(...)` share the most common
execution options:

| Option | Effect |
| --- | --- |
| `capture_output=False` | Let stdout/stderr pass through to the process streams instead of storing them on the result. |
| `raise_on_error=False` | Return a non-ok `PyPlyneExecutionResult` instead of raising parse, compile, or runtime failures. |
| `store_result=False` | Skip storing the final expression result as `result.result` and session `_`. |

Use the generated reference for the exact option set on each API.

## Retrieve Python Objects

PyPlyne executes in a normal Python environment. Values created by a run remain
available in the session, so Python can retrieve the actual live object rather
than parsing printed output.

Use a final expression when a snippet should return a value:

```python
import polars as pl
from pyplyne import run

sales = pl.DataFrame([
    {"region": "north", "amount": 120},
    {"region": "south", "amount": 80},
])

result = run("""
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""", context={"sales": sales})

summary = result.result
assert isinstance(summary, pl.DataFrame)
```

Use a named getter when a snippet creates one or more outputs:

```python
session = PyPlyneSession({"sales": sales})
session.run("""
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)
""")

summary = session.get_df("summary")
```

`session.get(name)` returns any named Python value. `session.get_df(name)` checks
that the value is a Polars DataFrame. `session.get_seq(name)` checks that the
value is a Python list or tuple. These helpers are the preferred public API for
reading outputs; `session.env` remains available for advanced integrations that
need direct access to the whole execution environment.

## Handle Errors

By default, `run(...)` raises parse, compile, or runtime errors. For agents,
web handlers, and other application workflows, ask for non-raising results and
inspect the result object:

```python
result = session.run("bad = seq 42\n", raise_on_error=False)

if not result.ok:
    print(result.phase)
    print(result.error)
    print(result.traceback)
```

`phase` tells you where the failure happened:

| Phase | Meaning |
| --- | --- |
| `parse` | The source text is not valid PyPlyne syntax. |
| `compile` | The source parsed, but could not be compiled into valid Python. |
| `runtime` | The generated Python raised while executing. |

The session server uses this same result model and formats diagnostics for text
or JSON responses. The Python result exposes raw fields such as `phase`,
`error`, `traceback`, and `shapes`; the HTTP JSON response adds a formatted
`diagnostic` object.

## Reuse State Deliberately

Create a new session when runs should be isolated. Reuse a session when the next
snippet should see names, imports, shapes, and `_` from earlier snippets.

```python
session = PyPlyneSession()

session.run('orders = seq [{"qty": 3}, {"qty": 0}]\n')
result = session.run("""
orders
  |> filter(qty > 0)
""")
```

If you need to expose host objects to PyPlyne, seed them through the session
constructor:

```python
def high_priority(order):
    return order["qty"] >= 10

session = PyPlyneSession({"high_priority": high_priority, "orders": orders})
session.run("urgent = seq orders |> filter(high_priority)\n")
```

## Compile Manually

Lower-level compiler helpers are available when you want direct control over
parsing, compilation, or generated Python code:

```python
from pyplyne import parse_source, compile_ast

tree = parse_source("numbers = seq [1, 2, 3]\n")
module = compile_ast(tree)
```

`compile_ast(...)` returns a Python `ast.Module`. If you execute the module
yourself, you are responsible for calling `compile(...)`, providing runtime
globals, and handling output or errors.

## Run Files

Use `run_file(...)` when you want to run a file once:

```python
from pyplyne import run_file

result = run_file("pipeline.pyplyne", context={"sales": sales})
summary = result.result
```

`PyPlyneSession` can also load a file into a persistent session:

```python
session = PyPlyneSession({"sales": sales})
result = session.load_file("pipeline.pyplyne")
summary = result.result
```

`run_file(...)` accepts the same non-raising and output-capture options as
`run(...)`:

```python
result = run_file("pipeline.pyplyne", raise_on_error=False)
```

`PyPlyneSession.load_file(...)` uses the default raising behavior. If you need
non-raising file execution in an existing session, read the file yourself and
call `session.run(..., raise_on_error=False)`:

```python
from pathlib import Path

result = session.run(
    Path("pipeline.pyplyne").read_text(encoding="utf-8"),
    filename="pipeline.pyplyne",
    raise_on_error=False,
)
```

For command-line execution, use `pyplyne run` or the shorthand `pyplyne SCRIPT`.

## Generated Reference

The public Python signatures and docstrings are generated from the package
source:

- [Generated Python API Reference](generated-python-api-reference)
