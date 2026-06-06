# Contributing

Thanks for helping improve PyPlyne.

## Development Setup

From a source checkout:

```bash
uv sync --extra dev
uv run pytest
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
- Run `uv run pytest` before opening a pull request.
- Run `npm run docs:check` from `site/` when changing docs, examples, editor
  grammar files, or docs generation scripts.

## Licensing

PyPlyne is licensed under the Apache License 2.0. Unless you explicitly say
otherwise, any contribution you intentionally submit to this repository is
provided under the same license.
