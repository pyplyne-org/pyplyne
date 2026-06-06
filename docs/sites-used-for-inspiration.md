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
