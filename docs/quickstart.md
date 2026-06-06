---
title: Quickstart
description: Install PyPlyne in your own project and run your first pipeline.
---

# Quickstart

This page gets PyPlyne installed in your own Python project and runs one
`.pyplyne` file. After that first run, the rest of the docs cover tables, files,
and interactive workflows.

## Requirements

PyPlyne requires Python 3.13 or newer. The commands below use `uv`.

Check your tools first:

```bash
uv --version
```

If Python 3.13 is not already available through `uv`, install it:

```bash
uv python install 3.13
```

## Install PyPlyne

Install PyPlyne in the project where you want to write pipelines:

```bash
uv init --python 3.13
uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"
```

If you already have a Python project, skip `uv init` and run the `uv add`
command from that project root. Until PyPlyne is published to PyPI, use the Git
URL for the package source. Git must be available on your machine. You can pin a
tag or commit by adding an `@ref` suffix to the Git URL when releases are
available.

If you use `pip`, install PyPlyne into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"
```

The commands below use `uv run pyplyne`. If you installed with `pip`, run
`pyplyne` directly from the activated environment.

Check that the CLI is available:

```bash
uv run pyplyne run --help
```

You should see help for running a `.pyplyne` script.

## Write a Sequence Pipeline

Create `hello.pyplyne`:

```pyplyne title="hello.pyplyne"
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)

print(result)
```

Run it:

```bash
uv run pyplyne hello.pyplyne
```

Expected output:

```text
[20, 40, 60]
```

`seq` marks the value as sequence-shaped. `filter` and `map` are sequence verbs,
and `_` is the current item inside each verb.

## Next Steps

- Read [Core Concepts](concepts.md) for the mental model.
- Read [Language Guide](language-guide.md) for table pipelines, files, and imports.
- Read [Interactive Sessions](interactive-sessions.md) for the REPL and `pyplyne serve`.
- Use [Examples](examples.md) and [Cookbook](cookbook.md) to copy working patterns.

## If You Cloned the Repository

If you are trying PyPlyne from a source checkout instead of installing it into a
separate project, run this from the repository root:

```bash
uv sync --extra dev
uv run pyplyne examples/list_pipeline.pyplyne
```

Use the same pattern for the other files in `examples/`:

```bash
uv run pyplyne examples/tabular_pipeline.pyplyne
```
