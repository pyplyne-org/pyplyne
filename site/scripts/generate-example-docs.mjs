import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(scriptDir, '..');
const projectRoot = path.resolve(siteDir, '..');
const catalogPath = path.join(siteDir, 'data', 'example-catalog.json');
const outputPath = path.join(projectRoot, 'docs', 'examples.md');

const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));

function readExample(relativePath) {
  const absolutePath = path.join(projectRoot, relativePath);
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`Example file does not exist: ${relativePath}`);
  }
  return fs.readFileSync(absolutePath, 'utf8').trimEnd();
}

function bulletList(items) {
  return items.map((item) => `- ${item}`).join('\n');
}

function exampleSection(example) {
  const code = readExample(example.file);
  return `## ${example.title}

${example.description}

\`\`\`bash
uv run pyplyne ${example.file}
\`\`\`

Shows:

${bulletList(example.concepts)}

\`\`\`pyplyne title="${example.file}"
${code}
\`\`\``;
}

const chooserRows = catalog
  .map((example) => `| ${example.title} | \`${example.file}\` |`)
  .join('\n');

const content = `---
title: Examples
description: Runnable PyPlyne examples included in the repository.
---

# Examples

These examples are checked into the PyPlyne repository. If you installed PyPlyne
in your own project, copy the snippets you want to try into a local
\`.pyplyne\` file and run that file with \`uv run pyplyne\`.

If you cloned this repository, run the examples from the repository root:

${catalog.map(exampleSection).join('\n\n')}

## Generated Output

The full tour writes \`examples/full_language_tour_output.csv\`. The generated
file is ignored by Git.

## Choosing An Example

| Goal | Example |
| --- | --- |
${chooserRows}

:::note Source-backed examples

This page is generated from \`site/data/example-catalog.json\` and the actual
files in \`examples/\`. Update the runnable example file first, then regenerate
this page with \`npm run docs:examples\` from \`site/\`.

:::
`;

fs.writeFileSync(outputPath, content);
console.log(`Generated ${path.relative(projectRoot, outputPath)} from ${catalog.length} examples.`);
