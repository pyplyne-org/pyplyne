import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(scriptDir, '..');
const projectRoot = path.resolve(siteDir, '..');
const outputPath = path.join(projectRoot, 'docs', 'generated-cli-reference.md');

const commands = [
  {
    title: 'Run',
    command: 'pyplyne run SCRIPT',
    purpose: 'Run a `.pyplyne` file.',
    args: ['run', '--help'],
  },
  {
    title: 'REPL',
    command: 'pyplyne repl',
    purpose: 'Start a persistent terminal REPL.',
    args: ['repl', '--help'],
  },
  {
    title: 'Serve',
    command: 'pyplyne serve',
    purpose: 'Start a persistent HTTP session.',
    args: ['serve', '--help'],
  },
  {
    title: 'Send',
    command: 'pyplyne send',
    purpose: 'Send source to a session server.',
    args: ['send', '--help'],
  },
];

function helpFor(args) {
  return execFileSync('uv', ['run', 'pyplyne', ...args], {
    cwd: projectRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trimEnd();
}

const commandRows = commands
  .map((command) => `| \`${command.command}\` | ${command.purpose} |`)
  .join('\n');

const sections = commands.map((command) => {
  const help = helpFor(command.args);
  const invocation = `pyplyne ${command.args.join(' ')}`;
  return `## ${command.title}

\`\`\`text title="${invocation}"
${help}
\`\`\``;
});

const content = `---
title: Generated CLI Help
description: Command help generated from the current PyPlyne CLI implementation.
---

# Generated CLI Help

This page is generated from the current \`pyplyne\` command implementation.
Update the CLI code first, then regenerate with \`npm run docs:cli\` from
\`site/\`.

## Commands

| Command | Purpose |
| --- | --- |
${commandRows}

The hand-written [CLI Reference](cli) includes examples and the \`pyplyne SCRIPT\`
shorthand. The sections below are exact help snapshots from the explicit
subcommands.

${sections.join('\n\n')}
`;

fs.writeFileSync(outputPath, content);
console.log(`Generated ${path.relative(projectRoot, outputPath)} from ${commands.length} commands.`);
