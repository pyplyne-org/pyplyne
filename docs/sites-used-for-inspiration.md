---
title: Sites Used For Inspiration
description: Python documentation sites that informed PyPlyne's documentation structure.
---

# Sites Used For Inspiration

This page keeps the useful parts of the docs research in one short maintainer
note. It is not a roadmap; it is a reference for the documentation patterns we
liked and the decisions they influenced.

## Python Documentation Inspiration

- **[Hydra](https://hydra.cc/docs/intro/)**
  Deep, task-oriented docs with tutorials, reference material, plugins,
  developer notes, and runnable examples.
- **[Great Expectations](https://docs.greatexpectations.io/docs/home/)**
  Clear audience paths, tested examples, and a strong distinction between
  learning material and reference material.
- **[Flet](https://flet.dev/docs/)**
  Generated API/reference pages and a polished Docusaurus presentation for a
  Python package.
- **[Apache Superset](https://superset.apache.org/user-docs/)**
  Audience-lane docs for users, administrators, and developers.
- **[dlt](https://dlthub.com/docs/)**
  Source-backed examples, generated docs artifacts, cookbook-style guidance, and
  agent-readable docs output.
- **[Dagster](https://docs.dagster.io/)**
  A practical split between user guide, examples, deployment/integration topics,
  and API lookup.

## Site Tooling Inspiration

- **[Docusaurus](https://docusaurus.io/docs)**
  Explicit sidebars, generated category indexes, broken-link checks, local
  search options, and a straightforward static-site build model.

## Packaging And Release Inspiration

- **[Python Packaging User Guide: GitHub Actions publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)**
  Tag-triggered distribution builds, artifact handoff between jobs, and PyPI
  publishing through GitHub Actions.
- **[PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)**
  OpenID Connect publishing without long-lived PyPI API tokens.
- **[setuptools-scm](https://setuptools-scm.readthedocs.io/en/latest/usage/)**
  Tag-derived package versions through `dynamic = ["version"]` in
  `pyproject.toml`.
- **[uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/)**
  `uv` setup and caching patterns for CI that match PyPlyne's local development
  workflow.
- **[PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)**
  PEP 440-compatible version syntax, including why release tags should use
  Python-compatible versions such as `v0.1.0`, `v0.2.0a1`, and `v0.2.0rc1`.
- **[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)**
  A simple branch-and-PR model where `main` is the integration branch and
  release readiness is proved by checks, review, and tags.
- **[git-flow releases](https://git-flow.readthedocs.io/en/latest/releases.html)**
  Useful contrast for larger projects that need separate release branches, even
  though PyPlyne does not need a permanent `dev` branch right now.
- **[release-please](https://github.com/googleapis/release-please-action)**
  Release-prep PR precedent: prepare changelogs and release metadata in a PR,
  then publish from the accepted release state.
- **[python-semantic-release](https://python-semantic-release.readthedocs.io/en/stable/configuration/automatic-releases/github-actions.html)**
  Python-specific automation precedent for CI-checked releases from GitHub.

## What PyPlyne Borrowed

- Keep the first-time path short: install, create one file, run it, then branch
  into deeper docs.
- Separate learning pages from lookup pages.
- Keep runnable examples in `examples/` and generate the examples page from
  those source files.
- Generate CLI and Python API references so docs do not drift from code.
- Keep cookbook recipes task-shaped instead of turning Quickstart into a manual.
- Publish a concise `llms.txt` so agents can find the right docs without reading
  the whole site.
- Derive package versions from release tags instead of hand-editing version
  strings.
- Use release-prep pull requests on `main` instead of maintaining a permanent
  `dev` branch.
- Keep PyPI publishing as a future tagged-release step; Git source installs stay
  documented until a package release exists.
- Treat `main` as development that may be ahead of the latest release; tags are
  the stable points users can pin.

## Maintenance Notes

PyPlyne keeps a small, explicit sidebar in `site/sidebars.js`. Hand-written
guides live in `docs/`. Generated pages and `site/static/llms.txt` should be
refreshed through the site scripts before release:

```bash
cd site
npm run docs:generate
npm run docs:highlighting
npm run docs:check
```

Use `npm run build` for a production-shaped docs check.
