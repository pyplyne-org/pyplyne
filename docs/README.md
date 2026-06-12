---
slug: /
title: PyPlyne Documentation
sidebar_position: 1
description: Learn PyPlyne, a Python-native way to write clean functional pipes for Polars tables and JSON-like records.
---

PyPlyne brings clean functional pipes directly to Python. It gives data
transformations a left-to-right shape while staying inside the Python runtime,
with Polars-first table workflows and compact sequence workflows for JSON-like
records.

Use this page to choose the next doc for your task. If you are new to PyPlyne,
start with the Quickstart. It shows how to install PyPlyne in your own project
and write your first pipelines.

## Where To Go

<div class="docs-card-grid">
  <a class="docs-card" href="/docs/quickstart">
    <span>Start</span>
    <strong>Quickstart</strong>
    <p>Install PyPlyne, run the CLI, and write your first pipeline.</p>
  </a>
  <a class="docs-card" href="/docs/concepts">
    <span>Understand</span>
    <strong>Core Concepts</strong>
    <p>Learn the execution model, pipeline shapes, and how PyPlyne works with Python.</p>
  </a>
  <a class="docs-card" href="/docs/language-guide">
    <span>Learn</span>
    <strong>Language Guide</strong>
    <p>Use the language day to day: syntax, table verbs, records, files, and imports.</p>
  </a>
  <a class="docs-card" href="/docs/sequence-patterns">
    <span>Compose</span>
    <strong>Sequence Patterns</strong>
    <p>Work with scalars, records, objects, functions, and other Python values in <code>seq</code> pipelines.</p>
  </a>
  <a class="docs-card" href="/docs/interactive-sessions">
    <span>Explore</span>
    <strong>Interactive Sessions</strong>
    <p>Keep data warm while iterating through the REPL, HTTP server, and <code>pyplyne send</code>.</p>
  </a>
  <a class="docs-card" href="/docs/reference">
    <span>Look up</span>
    <strong>Language Reference</strong>
    <p>Compact syntax, verb, aggregation, conversion, and file helper reference.</p>
  </a>
  <a class="docs-card" href="/docs/python-api">
    <span>Embed</span>
    <strong>Python API</strong>
    <p>Run PyPlyne from Python code and inspect the public runtime API.</p>
  </a>
  <a class="docs-card" href="/docs/cli">
    <span>Automate</span>
    <strong>CLI</strong>
    <p>Use command-line entry points for scripts, files, and interactive workflows.</p>
  </a>
  <a class="docs-card" href="/docs/troubleshooting">
    <span>Fix</span>
    <strong>Troubleshooting</strong>
    <p>Diagnose parser, runtime, import, file, and session issues.</p>
  </a>
</div>

## PyPlyne At A Glance

PyPlyne has two pipeline shapes:

- `df` for Polars-backed table transformations.
- `seq` for Python iterables, especially JSON-like records/lists.

Both shapes use `|>` to pass data through readable steps, and both execute
inside Python without generating `.py` files.

## Tiny Examples

```pyplyne
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
]

summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total = sum(amount), rows = count())
```

`df` tells PyPlyne the pipeline is table-shaped. Bare names inside table verbs,
such as `amount` and `region`, are compiled into Polars expressions.

```pyplyne
orders = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens", "qty": 2},
]

restock = orders
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
```

`seq` keeps record-oriented data in ordinary Python containers while giving you a
compact pipeline style for filtering, mapping, and reshaping.

## Common Tasks

- **Try the language:** [Quickstart](quickstart.md)
- **Understand `seq` vs. `df`:** [Core Concepts](concepts.md)
- **Write real transformations:** [Language Guide](language-guide.md)
- **Use objects and callables in sequence pipelines:** [Sequence Patterns](sequence-patterns.md)
- **Keep data warm while iterating:** [Interactive Sessions](interactive-sessions.md)
- **Find exact syntax:** [Language Reference](reference.md)
- **Use PyPlyne from Python:** [Python API](python-api.md)
- **Run from a terminal or agent:** [CLI](cli.md)
- **Copy working patterns:** [Examples](examples.md), [Package Inspirations](package-inspirations.md), and [Cookbook](cookbook.md)

## Reading Path

1. [Quickstart](quickstart.md) to install PyPlyne and run one file.
2. [Core Concepts](concepts.md) to understand `seq`, `df`, execution, and Python interop.
3. [Language Guide](language-guide.md) for table pipelines, files, and practical syntax.
4. [Sequence Patterns](sequence-patterns.md) to use `seq` with records, objects, and functions.
5. [Interactive Sessions](interactive-sessions.md) if you want a persistent REPL or agent-facing session.
6. [Language Reference](reference.md) when you need exact syntax or verb behavior.

## Project Status

PyPlyne is early-stage, and these docs describe the implementation in this
repository. The language surface is intentionally small: Python imports,
shape-aware verbs, Polars-backed table transforms, record helpers, file helpers,
and persistent sessions are the core pieces to learn first.
