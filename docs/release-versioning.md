---
title: Release And Versioning
description: Maintainer notes for PyPlyne package versions and future publishing.
---

# Release And Versioning

PyPlyne is not published to PyPI yet. User-facing install docs should keep using
the Git source install until the first package release is ready:

```bash
uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"
```

## Version Source

Package versions are derived from Git tags with `setuptools-scm`. The project
metadata in `pyproject.toml` declares `dynamic = ["version"]`, so maintainers do
not edit a hard-coded version string for each release.

Use PEP 440-compatible tags:

```text
v0.1.0
v0.1.1
v0.2.0
v0.2.0a1
v0.2.0rc1
```

Builds from an exact tag use that tag as the package version. Builds from
untagged commits become development versions derived from Git metadata, such as
`0.1.1.dev3+g<hash>` after a `v0.1.0` tag. If Git metadata is unavailable, the
configured fallback version is `0.0.0`.

## Release Shape

PyPlyne uses a small GitHub Flow-style release process. Work lands through pull
requests into `main`; there is no long-lived `dev` branch. A release-prep pull
request is a normal PR that gathers the final documentation, release notes, and
checklist updates for the next version. The CI workflow runs tests, builds the
package, smoke-tests the built distributions, and builds the docs site on every
PR.

`main` can be ahead of the latest released version. That is normal: `main` is
the latest accepted development state, while the latest release is the latest
release tag, and later the latest PyPI package. Users who need a stable version
should pin a tag rather than installing an unpinned branch.

For now, a release means a signed-off Git tag on the exact `main` commit that
passed release-prep CI. Users can pin that tag from the Git install URL:

```bash
uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git@v0.1.0"
```

Merging a release-prep PR does not publish a release by itself. It prepares a
known-good commit on `main`; the release happens when maintainers create and
push the version tag.

Before creating a release tag:

```bash
uv sync --locked --extra dev
uv run pytest
uv build
```

Also build the docs site when documentation, examples, editor grammar files, or
generated docs are touched:

```bash
cd site
npm run build
```

Then create and push the tag:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

If a patch release is needed after `main` has moved on, branch from the previous
release tag, make the minimal fix, open a PR, and tag the patch release from the
fixed commit. Merge or cherry-pick the fix forward so `main` does not lose it.

## Future PyPI Publishing

When PyPlyne is ready for PyPI, prefer GitHub Actions publishing from `v*` tags
using PyPI Trusted Publishing instead of long-lived API tokens. Keep publishing
separate from ordinary `main` pushes; release artifacts should come from a tag
that passed CI.

After the first PyPI release exists, update install docs from the Git URL to the
normal package install:

```bash
uv add pyplyne
```
