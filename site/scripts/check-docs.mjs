import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(scriptDir, '..');
const projectRoot = path.resolve(siteDir, '..');
const docsDir = path.join(projectRoot, 'docs');
const catalogPath = path.join(siteDir, 'data', 'example-catalog.json');
const llmsPath = path.join(siteDir, 'static', 'llms.txt');
const sidebarsPath = path.join(siteDir, 'sidebars.js');
const require = createRequire(import.meta.url);

function relativeProjectPath(filePath) {
  return path.relative(projectRoot, filePath).replaceAll(path.sep, '/');
}

function walkMarkdownFiles(directory) {
  return fs.readdirSync(directory, {withFileTypes: true}).flatMap((entry) => {
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return walkMarkdownFiles(absolutePath);
    }
    return entry.isFile() && entry.name.endsWith('.md') ? [absolutePath] : [];
  });
}

function frontmatterTextFor(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) {
    return null;
  }
  return match[1];
}

function frontmatterFor(filePath) {
  return frontmatterTextFor(fs.readFileSync(filePath, 'utf8'));
}

function parseFrontmatter(frontmatter) {
  if (!frontmatter) {
    return {};
  }
  return Object.fromEntries(
    frontmatter
      .split(/\r?\n/)
      .map((line) => line.match(/^([^:]+):\s*(.*)$/))
      .filter(Boolean)
      .map((match) => [match[1].trim(), match[2].trim().replace(/^["']|["']$/g, '')]),
  );
}

function docIdFor(filePath, frontmatter) {
  const relativePath = path.relative(docsDir, filePath).replaceAll(path.sep, '/');
  const inferredId = relativePath.replace(/\.md$/, '');
  if (!frontmatter.id) {
    return inferredId;
  }
  const directory = path.dirname(inferredId);
  return directory === '.' ? frontmatter.id : `${directory}/${frontmatter.id}`;
}

function routeFor(filePath, frontmatter) {
  if (frontmatter.slug === '/') {
    return '/docs/';
  }
  const relativePath = path.relative(docsDir, filePath).replaceAll(path.sep, '/');
  const stem = relativePath.replace(/\.md$/, '');
  return `/docs/${stem === 'README' ? '' : stem}`;
}

function collectSidebarDocIds(sidebars) {
  const ids = [];
  function walk(node) {
    if (typeof node === 'string') {
      ids.push(node);
      return;
    }
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    if (!node || typeof node !== 'object') {
      return;
    }
    if (node.type === 'doc' && node.id) {
      ids.push(node.id);
    } else if (node.id) {
      ids.push(node.id);
    }
    if (node.link?.type === 'doc' && node.link.id) {
      ids.push(node.link.id);
    }
    if (node.items) {
      walk(node.items);
    }
  }
  walk(Object.values(sidebars));
  return ids;
}

function duplicateValues(values) {
  const seen = new Set();
  const duplicates = new Set();
  for (const value of values) {
    if (seen.has(value)) {
      duplicates.add(value);
    }
    seen.add(value);
  }
  return [...duplicates].sort();
}

function parseLlmsEntries(text) {
  return text
    .split('\n')
    .map((line) => line.match(/^- \[(.+?)\]\((.+?)\):\s*(.*)$/))
    .filter(Boolean)
    .map((match) => ({title: match[1], route: match[2], description: match[3].trim()}));
}

const failures = [];
const markdownFiles = walkMarkdownFiles(docsDir);
const docs = markdownFiles.map((filePath) => {
  const relativePath = relativeProjectPath(filePath);
  const frontmatterText = frontmatterFor(filePath);
  const frontmatter = parseFrontmatter(frontmatterText);
  return {
    filePath,
    relativePath,
    frontmatterText,
    frontmatter,
    id: docIdFor(filePath, frontmatter),
    route: routeFor(filePath, frontmatter),
  };
});

for (const doc of docs) {
  if (!doc.frontmatterText) {
    failures.push(`${doc.relativePath} is missing frontmatter.`);
    continue;
  }
  for (const field of ['title', 'description']) {
    if (!doc.frontmatter[field]) {
      failures.push(`${doc.relativePath} is missing frontmatter field: ${field}.`);
    }
  }
}

for (const duplicateId of duplicateValues(docs.map((doc) => doc.id))) {
  failures.push(`Duplicate docs id: ${duplicateId}`);
}

let sidebars = {};
try {
  sidebars = require(sidebarsPath);
} catch (error) {
  failures.push(`Unable to load sidebars.js: ${error.message}`);
}

const sidebarDocIds = collectSidebarDocIds(sidebars);
const sidebarDocIdSet = new Set(sidebarDocIds);
const docsById = new Map(docs.map((doc) => [doc.id, doc]));

for (const duplicateSidebarId of duplicateValues(sidebarDocIds)) {
  failures.push(`Duplicate sidebar docs id: ${duplicateSidebarId}`);
}

for (const id of sidebarDocIdSet) {
  if (!docsById.has(id)) {
    failures.push(`Sidebar points to a missing docs page: ${id}`);
  }
}

for (const doc of docs) {
  if (!sidebarDocIdSet.has(doc.id) && doc.frontmatter.unlisted !== 'true') {
    failures.push(`${doc.relativePath} is not reachable from sidebars.js. Add it to the sidebar or set unlisted: true.`);
  }
}

if (!fs.existsSync(llmsPath)) {
  failures.push(`Missing generated llms.txt: ${path.relative(projectRoot, llmsPath)}`);
} else {
  const llmsEntries = parseLlmsEntries(fs.readFileSync(llmsPath, 'utf8'));
  const llmsRoutes = llmsEntries.map((entry) => entry.route);
  const llmsRouteSet = new Set(llmsRoutes);
  const listedDocs = docs.filter((doc) => doc.frontmatter.unlisted !== 'true');
  const listedDocRouteSet = new Set(listedDocs.map((doc) => doc.route));

  if (llmsEntries.length === 0) {
    failures.push('Generated llms.txt has no documentation entries.');
  }

  for (const duplicateRoute of duplicateValues(llmsRoutes)) {
    failures.push(`Duplicate llms.txt route: ${duplicateRoute}`);
  }

  for (const entry of llmsEntries) {
    if (!listedDocRouteSet.has(entry.route)) {
      failures.push(`llms.txt points to a missing docs route: ${entry.route}`);
    }
    if (!entry.title || !entry.description) {
      failures.push(`llms.txt entry needs a title and description: ${entry.route}`);
    }
  }
}

const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
const catalogFiles = catalog.map((example) => example.file).filter(Boolean);
const catalogTitles = catalog.map((example) => example.title).filter(Boolean);
const exampleFiles = fs
  .readdirSync(path.join(projectRoot, 'examples'), {withFileTypes: true})
  .filter((entry) => entry.isFile() && entry.name.endsWith('.pyplyne'))
  .map((entry) => `examples/${entry.name}`)
  .sort();
const catalogFileSet = new Set(catalogFiles);

for (const duplicateFile of duplicateValues(catalogFiles)) {
  failures.push(`Duplicate example catalog file: ${duplicateFile}`);
}

for (const duplicateTitle of duplicateValues(catalogTitles)) {
  failures.push(`Duplicate example catalog title: ${duplicateTitle}`);
}

for (const file of exampleFiles) {
  if (!catalogFileSet.has(file)) {
    failures.push(`Example file is missing from catalog: ${file}`);
  }
}

for (const example of catalog) {
  if (!example.title || !example.file || !example.description) {
    failures.push(`Example catalog entry is missing title, file, or description: ${JSON.stringify(example)}`);
    continue;
  }
  const examplePath = path.join(projectRoot, example.file);
  if (!fs.existsSync(examplePath)) {
    failures.push(`Example catalog points to a missing file: ${example.file}`);
  }
  if (!Array.isArray(example.concepts) || example.concepts.length === 0) {
    failures.push(`Example catalog entry needs at least one concept: ${example.file}`);
  }
  try {
    execFileSync('uv', ['run', 'pyplyne', example.file], {
      cwd: projectRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (error) {
    failures.push(`Example failed to run: ${example.file}\n${error.stderr || error.stdout || error.message}`);
  }
}

if (failures.length > 0) {
  console.error(failures.join('\n'));
  process.exit(1);
}

console.log(`Checked ${docs.length} docs, ${sidebarDocIds.length} sidebar entries, and ${catalog.length} examples.`);
