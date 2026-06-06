# PyPlyne Site

This Docusaurus site renders the canonical Markdown docs from `../docs` and
adds a small custom landing page.

From the repository root, install the Python development environment first when
you want generated CLI/API docs and runnable examples to work:

```bash
uv sync --extra dev
```

Then start the docs site:

```bash
cd site
npm install
npm run start
```

The site package includes the reusable browser syntax highlighter as a local
file dependency:

```json
{
  "dependencies": {
    "prism-pyplyne": "file:../packages/prism-pyplyne"
  }
}
```

PyPlyne Markdown code fences use `pyplyne`. Docusaurus loads that grammar through
the `src/theme/prism-include-languages.js` theme override, which calls
`require('prism-pyplyne')` after binding Docusaurus' Prism instance to
`globalThis.Prism`.

Build the static site with:

```bash
npm run build
```

Useful maintenance commands:

```bash
npm run docs:generate  # regenerate examples, CLI/API reference, and llms.txt
npm run docs:highlighting # verify the local Prism grammar package
npm run docs:check     # regenerate docs artifacts, validate frontmatter, and run cataloged examples
npm run docs:check:clean # docs:check, then fail if generated artifacts changed
npm run build          # run docs:check and fail on Docusaurus build/link issues
```

Use `npm run docs:check` before handing off docs changes. It keeps the generated
docs artifacts source-backed, then checks that every docs page has `title` and
`description` frontmatter, is reachable from `sidebars.js` unless explicitly
`unlisted: true`, appears in `static/llms.txt`, and that cataloged examples
still execute.

`docs:check` intentionally mutates generated files. Use `npm run
docs:check:clean` in CI or before a release when you want to prove the generated
Markdown and `llms.txt` were already fresh in git.

When adding or moving docs pages:

- add the page to `../docs` with frontmatter before wiring it into the sidebar
- update `sidebars.js` so the page is discoverable, or mark intentionally hidden
  pages with `unlisted: true`
- update runnable examples and `data/example-catalog.json` together, then run
  `npm run docs:generate`
- run `npm run build` when changing links, routes, generated docs, or sidebar
  structure; Docusaurus is configured to throw on broken site and Markdown links

Local search is generated during the production build, so it appears in
`npm run build` / `npm run serve` output rather than during `npm run start`.
