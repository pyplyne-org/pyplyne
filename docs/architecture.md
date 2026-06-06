---
title: Architecture
description: How PyPlyne parses, compiles, and executes custom syntax through Python AST.
---

# Architecture

## Executive Summary

PyPlyne brings clean functional pipes directly to Python. It is a lightweight
Domain-Specific Language for writing data and file transformations left to
right, then compiling that custom syntax directly into native Python AST nodes
and executing the tree in-memory with CPython bytecode.

This keeps the language fast, interoperable with Python imports, and debuggable
without generating temporary `.py` files. The architecture is intentionally
small: a Lark grammar recognizes PyPlyne syntax, a compiler lowers the parse tree
into Python AST, runtime helpers implement the pipeline verbs, and sessions keep
execution state for interactive workflows.

## Execution Pipeline

PyPlyne has one compile-and-run path for files, the CLI, the REPL, and the HTTP
session server:

1. Parse: `parse_source()` reads PyPlyne source with the cached Lark parser from
   `grammar.lark`. The parser uses Earley parsing, resolves ambiguities, and
   propagates token positions so later phases can attach useful line and column
   information to generated Python AST nodes.
2. Transform: `compile_ast()` delegates to `AstBuilder`, which walks the Lark
   tree and emits a native `ast.Module`. This phase lowers imports,
   assignments, literals, calls, lambdas, pipe expressions, and shape
   annotations into Python AST nodes.
3. Compile: the generated module is passed through
   `ast.fix_missing_locations()` and then to
   `compile(module, filename=source_path, mode="exec")`. CPython returns a code
   object; PyPlyne does not emit an intermediate Python source file.
4. Run: `exec()` evaluates the code object inside an environment seeded by
   `runtime_globals()`. That environment provides the sequence helpers, table
   helpers, coercion helpers, file readers/writers, and Python builtins.
5. Persist: `PyPlyneSession` optionally wraps the same path in a long-lived
   environment, preserving imports, variables, shape metadata, and the most
   recent expression result across snippets.

The important boundary is between transformation and runtime. The compiler is
responsible for syntax, shape validation, and expression rewriting. The runtime
is responsible for actual values: iterating sequences, building or collecting
Polars frames, reading files, and raising type errors for data that cannot be
coerced.

## MVP Scope

- Functional pipeline operator: `value |> call(...)`.
- RHS shape annotations for pipeline sources: `name = seq ...` and
  `name = df ...`.
- Native Python imports.
- Native AST compilation with source line and column mapping.
- Functional list helpers inspired by purrr.
- Tabular helpers inspired by dplyr and executed through Polars, preferably as
  lazy internal query plans with concrete results by default.
- Concise sequence lambdas through `_` placeholders, numbered placeholders, and
  explicit arrow lambdas.
- Persistent execution sessions for iterative work, exposed through a terminal
  REPL and a small HTTP server.

## Compiler Layers

### Parser

The grammar accepts a compact subset of Python-like expressions plus PyPlyne's
pipeline and shape syntax. It keeps parsing focused on structure:

- statements: imports, assignments, expressions, and blank lines;
- expressions: literals, calls, attributes, subscripts, booleans, arithmetic,
  comparisons, and lambdas;
- PyPlyne extensions: `|>`, `.method(...)` pipes, RHS `df`/`seq` annotations,
  and `defer`.

Parsing does not infer shapes or execute code. It returns a positioned Lark
parse tree and leaves semantic decisions to `AstBuilder`.

### AST Builder

`AstBuilder` is the compiler's semantic layer. It lowers PyPlyne constructs to
Python nodes that CPython already understands:

- `x = ...` becomes `ast.Assign`;
- `import` and `from ... import ...` become native import nodes;
- `value |> f(a)` becomes a call shaped like `f(value, a)`;
- `value |> .method(a)` becomes `value.method(a)`;
- `_`, `_1`, and explicit arrow callbacks become `ast.Lambda` nodes;
- `df` and `seq` annotations become calls to `_as_df(...)` or `_as_seq(...)`;
- ordinary assignment and expression boundaries are wrapped in `_auto(...)`
  unless the expression is explicitly marked with `defer`.

The builder also owns the compile-time shape registry. That registry records
which names are known `df` or `seq` values and validates that each pipeline verb
is used with the right current shape. Conversion verbs such as `to_rows()` and
`to_table()` deliberately move a pipeline from one shape family to the other.
Terminal sequence verbs such as `reduce()` return a scalar and clear the stored
shape for the assigned name.

### Expression Rewriters

PyPlyne has two small AST rewriters for expression contexts:

- `TableExprRewriter` converts bare names inside tabular verbs into Polars
  expressions. For example, `where(amount > 100)` is lowered toward
  `_col("amount") > 100`, and boolean `and`/`or` become expression-compatible
  operators.
- `RowExprRewriter` converts bare names inside record-style sequence filters
  and row-record helpers into runtime field lookups. For example,
  `filter(amount > 100)` lowers to a row predicate that reads a dictionary
  field or object attribute, while `filter(is_valid)` remains a direct
  predicate function.

These rewrites happen before CPython compilation, so callback and expression
syntax still runs as normal Python bytecode after lowering.

## Core Semantic Decisions

### Pipeline Shapes

`seq` and `df` are right-hand-side annotations on expressions. They tell the
compiler how to treat a raw pipeline source. The assigned variable records the
final shape of the whole expression, which may differ from the starting shape.

```pyplyne
values = seq [1, 2, 3]
sales = df read_csv("sales.csv")
total = seq load_values() |> reduce(_1 + _2)
```

The important invariant is that a pipeline's current shape must match the verb
family being compiled. Conversion helpers intentionally change that shape.
Terminal verbs such as `reduce` can return a scalar and clear the assigned
variable's stored shape.

At runtime, annotations also normalize source values. A `df` annotation produces
a Polars `DataFrame`, including when the source value is a list of dictionaries
or another table-shaped object. A `seq` annotation stores sequence-shaped data.

### Run-by-default Execution

PyPlyne scripts run by default. Table helpers use Polars lazy query plans where
that preserves the table pipeline, but assignment and expression boundaries
auto-materialize lazy plans into concrete Polars `DataFrame` values.

Use `defer` to preserve a lazy plan:

```pyplyne
plan = defer sales
  |> where(amount > 100)
  |> select(region, amount)
```

Avoid adding `df` around a lazy plan you want to preserve, because `df`
normalization can collect lazy frames.

`collect()` remains available because Polars users expect it, but it is not the
ordinary execution boundary for PyPlyne. It also does not perform shape
conversion; `to_rows()` and `to_table()` are the explicit table/sequence
boundaries.

### Tabular Expression Mode

Inside table verbs such as `where`, `mutate`, `select`, `group_by`,
`summarize`, and `arrange`, bare identifiers are column references. The compiler
rewrites those identifiers to Polars expressions before emitting Python AST.

For example:

```pyplyne
result = sales
  |> where(amount > 100 and region == "north")
  |> mutate(net = amount - discount)
  |> select(region, amount, net)
```

is executed by the Polars backend, not by Python row-by-row lambdas.

### Runtime Helpers

The runtime namespace is the execution surface that compiled PyPlyne code calls
into. It includes:

- sequence helpers: `map`, `filter`, `reduce`, `set_fields`, `drop_fields`, and
  `keep_fields`;
- table helpers: `select`, `where`, `mutate`, `group_by`, `summarize`, and
  `arrange`;
- shape and materialization helpers: `_as_df`, `_as_seq`, `_auto`, `collect`,
  `to_rows`, and `to_table`;
- file helpers: `read_csv`, `read_json`, `read_parquet`, `read_excel`, and the
  matching write helpers.

Most table helpers normalize table-shaped values to a Polars `LazyFrame` for
the duration of the table operation. `_auto()` collects lazy frames at ordinary
run boundaries and rejects unfinished grouped plans, which keeps scripts
run-by-default while still allowing explicit lazy execution through `defer`.

### Persistent Sessions

PyPlyne supports interactive execution through a long-lived session object. A
session owns both a Python execution environment and the compiler's shape
registry, so imports, loaded data, intermediate variables, and `seq`/`df`
shape annotations persist between snippets.

The same session model powers the terminal REPL, HTTP session server, and
`pyplyne send` client. See [Interactive Sessions](interactive-sessions.md) for
user-facing workflows.

Expression snippets store their result as `_`, mirroring Python-style
interactive exploration while still preserving shape information where it can
be inferred from the runtime value.

The compiler distinguishes session `_` from lambda placeholder `_` by syntactic
position. If the previous session result is scalar, the session clears `_` from
the shape registry so shaped pipeline verbs cannot be applied to stale shape
information.

On failure, the session does not wholesale replace its shape registry with a
failed compile's assumptions. It reconciles shape metadata with names that still
exist in the environment, which makes parse, compile, and runtime errors easier
to recover from in the REPL and HTTP server.

### Sequence Lambda Syntax

Sequence verbs such as `map`, `filter`, and `reduce` run on ordinary Python
iterables. Their callback arguments may use concise placeholder syntax:

```pyplyne
numbers = seq [1, 2, 3, 4]

doubled = numbers
  |> filter(_ > 10)
  |> map(_ * 2)
```

The compiler rewrites those callback expressions into native Python lambdas.

Numbered placeholders support multi-argument callbacks:

```pyplyne
numbers |> reduce(_1 + _2)
```

Explicit arrow lambdas are available when parameter names are clearer:

```pyplyne
numbers |> map(x => x * 2)
numbers |> reduce((total, x) => total + x)
```

These forms compile to native Python lambda AST nodes rather than being
interpreted by a separate runtime.

## Future Scope

- A richer parser for broader Python expression coverage.
- Static DAG extraction and visualization.
- A language server and syntax highlighting.
- Optional safety policy controls for sandboxed execution.
