import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const Prism = require('prismjs');
require('prism-pyplyne');

const sample = `from pathlib import Path

sales = df read_csv("sales.csv")
summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total=sum(amount), rows=count())

orders = seq [
  {"item": "pens", "qty": 2},
  {"item": "paper", "qty": 1},
]
reviewed = orders
  |> filter(qty > 1)
  |> set_fields(buy=item == "pens")
  |> keep_fields(item, buy)
`;

assert.ok(Prism.languages.pyplyne, 'expected Prism language pyplyne to be registered');
assert.equal(Prism.languages[['pl', 'yne'].join('')], undefined, 'expected old short language id not to be registered');

const html = Prism.highlight(sample, Prism.languages.pyplyne, 'pyplyne');
for (const token of [
  'token keyword',
  'token function',
  'token operator',
  'token string',
  'token number',
]) {
  assert.ok(html.includes(token), `expected highlighted HTML to include ${token}`);
}

console.log('Checked Prism PyPlyne grammar.');
