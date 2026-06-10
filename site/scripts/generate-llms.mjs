import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(scriptDir, '..');
const projectRoot = path.resolve(siteDir, '..');
const docsDir = path.join(projectRoot, 'docs');
const outputPath = path.join(siteDir, 'static', 'llms.txt');
const sectionOrder = ['Start Here', 'Use The Language', 'Runtime Interfaces', 'Reference'];
const docOrder = [
  'README',
  'quickstart',
  'concepts',
  'language-guide',
  'sequence-patterns',
  'examples',
  'cookbook',
  'package-inspirations',
  'package-inspirations/purrr',
  'package-inspirations/dplyr',
  'interactive-sessions',
  'editor',
  'reference',
  'cli',
  'generated-cli-reference',
  'python-api',
  'generated-python-api-reference',
  'troubleshooting',
];
const docSections = new Map([
  ['README', 'Start Here'],
  ['quickstart', 'Start Here'],
  ['concepts', 'Start Here'],
  ['language-guide', 'Use The Language'],
  ['sequence-patterns', 'Use The Language'],
  ['examples', 'Use The Language'],
  ['cookbook', 'Use The Language'],
  ['package-inspirations', 'Use The Language'],
  ['package-inspirations/purrr', 'Use The Language'],
  ['package-inspirations/dplyr', 'Use The Language'],
  ['interactive-sessions', 'Runtime Interfaces'],
  ['editor', 'Runtime Interfaces'],
  ['reference', 'Reference'],
  ['cli', 'Reference'],
  ['generated-cli-reference', 'Reference'],
  ['python-api', 'Reference'],
  ['generated-python-api-reference', 'Reference'],
  ['troubleshooting', 'Reference'],
]);
const llmsDocIds = new Set(docOrder);

function walkMarkdownFiles(directory) {
  return fs.readdirSync(directory, {withFileTypes: true}).flatMap((entry) => {
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return walkMarkdownFiles(absolutePath);
    }
    return entry.isFile() && entry.name.endsWith('.md') ? [absolutePath] : [];
  });
}

function frontmatterFor(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) {
    return {};
  }
  return Object.fromEntries(
    match[1]
      .split(/\r?\n/)
      .map((line) => line.match(/^([^:]+):\s*(.*)$/))
      .filter(Boolean)
      .map((match) => [match[1].trim(), match[2].trim().replace(/^["']|["']$/g, '')]),
  );
}

function routeFor(filePath, frontmatter) {
  if (frontmatter.slug === '/') {
    return '/docs/';
  }
  const relativePath = path.relative(docsDir, filePath).replaceAll(path.sep, '/');
  const stem = relativePath.replace(/\.md$/, '');
  return `/docs/${stem === 'README' ? '' : stem}`;
}

const docs = walkMarkdownFiles(docsDir)
  .map((filePath) => {
    const text = fs.readFileSync(filePath, 'utf8');
    const frontmatter = frontmatterFor(text);
    const relativePath = path.relative(docsDir, filePath).replaceAll(path.sep, '/').replace(/\.md$/, '');
    const name = path.basename(filePath, '.md');
    const order = docOrder.indexOf(name);
    return {
      title: frontmatter.title || path.basename(filePath, '.md'),
      description: frontmatter.description || '',
      order: order === -1 ? Number.POSITIVE_INFINITY : order,
      relativePath,
      route: routeFor(filePath, frontmatter),
      section: docSections.get(relativePath) || docSections.get(name) || 'Project Notes',
      unlisted: frontmatter.unlisted === 'true',
    };
  })
  .filter((doc) => !doc.unlisted && llmsDocIds.has(doc.relativePath))
  .sort((left, right) => {
    const sectionCompare = sectionOrder.indexOf(left.section) - sectionOrder.indexOf(right.section);
    const orderCompare = left.order - right.order;
    return sectionCompare || orderCompare || left.route.localeCompare(right.route);
  });

function linkFor(doc) {
  return `- [${doc.title}](${doc.route}): ${doc.description}`;
}

function sectionFor(title) {
  const links = docs.filter((doc) => doc.section === title).map(linkFor);
  return links.length ? `### ${title}\n\n${links.join('\n')}` : '';
}

const content = `# PyPlyne

> PyPlyne is a Python-friendly pipeline language for fast, readable data transformations over Polars tables and Python sequences.

Use this file when helping someone install, write, run, debug, or embed PyPlyne.
Prefer practical syntax and runtime guidance over implementation details.

## Install And Run

- Requires Python 3.13 or newer.
- Package name and CLI command: \`pyplyne\`.
- Until PyPlyne is published to PyPI, install from Git in the user's own project:
  \`uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"\`.
- If the user is starting a new project, run \`uv init --python 3.13\` first.
- If the user already has a Python project, run \`uv add\` from that project root.
- With \`pip\`, install into an activated virtual environment:
  \`python -m pip install "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"\`.
- Run a file once with \`uv run pyplyne script.pyplyne\` or, from an activated
  pip environment, \`pyplyne script.pyplyne\`.
- For a first successful file, create a \`.pyplyne\` script that prints a result
  and run it once before moving on to tables, files, or sessions.
- Repository-only examples are useful references, but do not assume the user is
  running from a PyPlyne source checkout.

## Core Syntax

PyPlyne code is ordinary-looking Python plus left-to-right pipe syntax. Files use
the \`.pyplyne\` extension.

- Shape annotations go on the right-hand side: \`name = seq expression\` or \`name = df expression\`.
- \`seq\` means non-string, non-mapping Python iterable data; Polars tables become row dictionaries.
- \`df\` means table-shaped data; PyPlyne normalizes it to a Polars DataFrame.
- Pipe with \`|>\`: \`source |> verb(args)\`.
- Once a variable is known as \`seq\` or \`df\`, later pipelines can start from it.
- If a pipeline starts from an unshaped value, annotate the source with \`seq\` or \`df\`.
- Convert explicitly between shapes with \`to_rows()\` and \`to_table()\`.
- Imports work normally: \`import polars as pl\`, \`from scoring import score_order\`.

## Table Pipelines

Use \`df\` for Polars-backed table workflows. Bare identifiers inside table verbs
are column expressions.

\`\`\`pyplyne
sales = df read_csv("sales.csv")

summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total = sum(amount), average = mean(amount))
  |> arrange(total)
\`\`\`

Common table verbs:

- \`where(expr)\`: filter rows.
- \`mutate(name = expr, ...)\`: add or replace columns.
- \`select(col, ...)\`: project columns.
- \`group_by(col, ...)\`: group rows for aggregation.
- \`summarize(name = aggregate, ...)\`: aggregate grouped or whole-table data.
- \`arrange(col)\`: sort.
- \`collect()\`: use Polars' collection/materialization behavior.

## Sequence Pipelines

Use \`seq\` for Python iterables. In sequence callbacks, \`_\` is the current item.
For multi-argument callbacks such as \`reduce\`, use \`_1\` and \`_2\`.

\`\`\`pyplyne
numbers = seq [1, 2, 3, 4, 5, 6]

result = numbers
  |> filter(_ % 2 == 0)
  |> map(_ * 10)
\`\`\`

For JSON-like records, bare field names are convenient inside record filters and updates:

\`\`\`pyplyne
orders = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens", "qty": 2},
]

restock = orders
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
\`\`\`

Common sequence verbs:

- \`map(expr)\`: transform every item.
- \`filter(expr)\`: keep items whose expression is truthy.
- \`reduce(expr)\`: collapse a sequence to one scalar.
- \`set_fields(name = expr, ...)\`: add/replace fields on record dictionaries.
- \`drop_fields(field, ...)\`: remove fields from record dictionaries.
- \`keep_fields(field, ...)\`: project fields from record dictionaries.
- In \`filter(...)\`, bare names can read dictionary fields or object attributes.
- In record field verbs, rows must be dictionaries.
- Missing fields are boolean-false; \`==\` and ordering comparisons do not match, while \`!=\` matches.

## Moving Between Tables And Sequences

- \`to_rows()\` converts a \`df\` pipeline to a \`seq\` of row dictionaries.
- \`to_table()\` converts a \`seq\` of row dictionaries to a Polars-backed \`df\`.
- Use this boundary for row-wise Python functions, object logic, or JSON-style edits.

\`\`\`pyplyne
reviewed = df read_csv("sales.csv")
  |> where(amount > 100)
  |> to_rows()
  |> set_fields(reviewed=True)
  |> to_table()
  |> arrange(region)
\`\`\`

## Python API

Use \`run(...)\` for one isolated execution and \`PyPlyneSession\` for persistent
state across many snippets.

\`\`\`python
import polars as pl
from pyplyne import run, PyPlyneSession

sales = pl.DataFrame([
    {"region": "north", "amount": 120},
    {"region": "south", "amount": 80},
])

result = run("""
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""", context={"sales": sales})

summary = result.result
\`\`\`

\`PyPlyneSession\` keeps variables, imports, known \`seq\`/\`df\` shapes, and the
last expression result \`_\` alive. Use \`session.get(name)\`,
\`session.get_df(name)\`, and \`session.get_seq(name)\` to retrieve live Python
objects.

## Agent Session Loop

For agents iterating against loaded data, prefer a warm session server plus
\`pyplyne send --json\`. Start the server once, usually with setup preloaded:

\`\`\`bash
uv run pyplyne serve --port 8765 --load setup.pyplyne
\`\`\`

For multiline snippets, send source through stdin with a heredoc rather than
packing it into \`--expr\`:

\`\`\`bash
uv run pyplyne send --json <<'PYPLYNE'
summary = df sales
  |> group_by(region)
  |> summarize(total = sum(amount))

summary
PYPLYNE
\`\`\`

\`--source-name\` is optional metadata for diagnostics, not a file input. Add it
only when generated or editor-buffer source needs a stable label, such as
\`--source-name agent-step-01.pyplyne\`. Otherwise PyPlyne uses a generated
session label.

## Error Guidance

- Parse errors mean the source is not valid PyPlyne syntax.
- Compile errors usually mean a shape/verb mismatch, such as using \`where\` on
  \`seq\` data or \`map\` on \`df\` data.
- Runtime errors come from the generated Python/Polars execution.
- For agents, prefer \`pyplyne send --json\` or Python \`raise_on_error=False\`
  so diagnostics can be inspected structurally.
- If a pipeline has unknown shape, add \`seq\` or \`df\` at the source.
- If a verb family is wrong, convert explicitly with \`to_rows()\` or \`to_table()\`.

## Best Documentation To Fetch

${sectionOrder.map(sectionFor).filter(Boolean).join('\n\n')}
`.replace(/\n{3,}/g, '\n\n');

fs.writeFileSync(outputPath, content);
console.log(`Generated ${path.relative(projectRoot, outputPath)} from ${docs.length} docs.`);
