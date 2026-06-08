# Contributing

Thanks for helping improve PyPlyne.

## Development Setup

From a source checkout:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=pyplyne --cov-report=term-missing
```

The docs site lives in `site/`:

```bash
cd site
npm install
npm run docs:check
```

## Pull Requests

- Keep changes focused on one behavior, bug, or documentation improvement.
- Add or update tests when behavior changes.
- Run `uv run ruff check .` and `uv run ruff format --check .` before opening
  a pull request.
- Run `uv run pytest --cov=pyplyne --cov-report=term-missing` before opening a
  pull request.
- Run `npm run docs:check` from `site/` when changing docs, examples, editor
  grammar files, or docs generation scripts.

## Releases And Versions

PyPlyne uses tag-derived package versions through `setuptools-scm`. Do not edit
a hard-coded package version for release commits. Use PEP 440-compatible Git
tags such as `v0.1.0`, `v0.1.1`, `v0.2.0a1`, or `v0.2.0rc1`.

Release prep happens through a normal pull request into `main`; there is no
long-lived `dev` branch. It is fine for `main` to contain unreleased commits.
The latest stable version is the latest release tag, and later the latest PyPI
package.

PyPlyne is not published to PyPI yet, so install docs should keep using the Git
source URL until the first package release exists. See the Release And
Versioning project note for the maintainer checklist.

## Licensing

PyPlyne is licensed under the Apache License 2.0. Unless you explicitly say
otherwise, any contribution you intentionally submit to this repository is
provided under the same license.
