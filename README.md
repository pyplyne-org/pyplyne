<p align="center">
  <img src="site/static/img/pyplyne-icon.svg" alt="PyPlyne logo" width="96" height="96">
</p>

# PyPlyne

PyPlyne brings clean functional pipes directly to Python, so data transformations
read left to right without leaving the Python runtime.

It is a small DSL that compiles directly into native Python AST nodes and
executes in-memory with CPython bytecode. Table workflows are Polars-first,
while sequence workflows use compact pipeline syntax for JSON-like records.

```pyplyne
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)
```

## Quick Start

Add PyPlyne to the Python project where you want to write pipelines:

```bash
uv init --python 3.13
uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"
```

If you already have a Python project, skip `uv init` and run `uv add` from that
project root. Until PyPlyne is published to PyPI, use the Git URL for the
package source. Git must be available on your machine. You can pin a tag or
commit by adding an `@ref` suffix to the Git URL when releases are available.

If you use `pip`, install PyPlyne into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"
```

The commands below use `uv run pyplyne`. If you installed with `pip`, run
`pyplyne` directly from the activated environment.

Then create `pipeline.pyplyne`:

```pyplyne
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)

print(result)
```

Run it once:

```bash
uv run pyplyne pipeline.pyplyne
```

You should see `[20, 40, 60]`.

Next, read the [Quickstart](docs/quickstart.md) or the
[Language Guide](docs/language-guide.md) for table pipelines, files, and
interactive workflows.

## Documentation

- [PyPlyne docs overview](docs/README.md)
- [Quickstart](docs/quickstart.md)
- [Core concepts](docs/concepts.md)
- [Language guide](docs/language-guide.md)
- [Language reference](docs/reference.md)
- [CLI reference](docs/cli.md)
- [Interactive sessions](docs/interactive-sessions.md)
- [Examples](docs/examples.md)
- [VS Code extension](docs/editor.md)
- [Python API](docs/python-api.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)

## License

PyPlyne is licensed under the [Apache License 2.0](LICENSE).

## Source Checkout

If you cloned this repository to work on PyPlyne or try the checked-in examples,
set up the development environment from the repo root:

```bash
uv sync --extra dev
uv run pyplyne examples/list_pipeline.pyplyne
```

From a source checkout, run the test suite with:

```bash
uv run pytest
```
