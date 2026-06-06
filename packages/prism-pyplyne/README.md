# prism-pyplyne

Prism syntax highlighting grammar for PyPlyne pipeline code.

The package registers the `pyplyne` language name with Prism for PyPlyne docs
and websites.

## Install

Install it anywhere you already use Prism:

```bash
npm install prism-pyplyne prismjs
```

Docusaurus sites already depend on Prism through the classic preset, so they
usually only need:

```bash
npm install prism-pyplyne
```

When developing this repository's docs site, the site package installs the local
workspace package instead:

```json
{
  "dependencies": {
    "prism-pyplyne": "file:../packages/prism-pyplyne"
  }
}
```

## Use With Prism

```js
const Prism = require('prismjs');
require('prism-pyplyne');

const html = Prism.highlight(
  'summary = df sales\\n  |> where(amount > 100)',
  Prism.languages.pyplyne,
  'pyplyne',
);
```

## Use With Docusaurus

Docusaurus uses Prism for code blocks. Install the package in the Docusaurus
site package, then add it to a `src/theme/prism-include-languages.js` theme
override:

```js
export default function prismIncludeLanguages(PrismObject) {
  const previousPrism = globalThis.Prism;
  globalThis.Prism = PrismObject;

  require('prism-pyplyne');

  delete globalThis.Prism;
  if (typeof previousPrism !== 'undefined') {
    globalThis.Prism = previousPrism;
  }
}
```

Then use `pyplyne` as the Markdown code fence language:

````md
```pyplyne
rows = seq orders
  |> filter(qty > 1)
  |> set_fields(buy=item == "pens")
```
````

The import is intentionally side-effectful: loading `prism-pyplyne` registers
`Prism.languages.pyplyne`.
