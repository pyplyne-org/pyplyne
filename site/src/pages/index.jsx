import {useCallback, useEffect, useRef, useState} from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import Prism from 'prismjs';
import pyplyneGrammar from 'prism-pyplyne';
import styles from './index.module.css';

Prism.languages.pyplyne = pyplyneGrammar;
Prism.languages.python = Prism.languages.python || {
  comment: /#.*/,
  string: {
    pattern: /(?:[rubf]|br|rb)?(["'])(?:\\[\s\S]|(?!\1)[^\\\r\n])*\1/i,
    greedy: true,
  },
  keyword: /\b(?:as|class|def|from|import|in|lambda|return|with)\b/,
  boolean: /\b(?:False|None|True)\b/,
  function: /\b[A-Za-z_]\w*(?=\s*\()/,
  number: /\b\d+(?:\.\d+)?\b/,
  operator: /[-+*/%=<>!]+/,
  punctuation: /[()[\]{},.:]/,
};
Prism.languages.bash = Prism.languages.bash || {
  string: {
    pattern: /(["'])(?:\\[\s\S]|(?!\1)[^\\\r\n])*\1/,
    greedy: true,
  },
  parameter: /--[A-Za-z0-9-]+/,
  function: /\b(?:pyplyne|uv)\b/,
  number: /\b\d+\b/,
  operator: /[|&;=]/,
};

const features = [
  {
    label: 'Pipeline syntax',
    title: 'Read transformations left to right.',
    text: 'Pipe data through named steps instead of nesting function calls or spreading a simple flow across temporary variables.',
    href: '/docs/language-guide',
  },
  {
    label: 'Two data shapes',
    title: 'Use df for tables and seq for records.',
    text: 'Table pipelines are Polars-backed. Sequence pipelines work well for lists of JSON-like Python records.',
    href: '/docs/reference',
  },
  {
    label: 'Python runtime',
    title: 'Stay inside Python, not beside it.',
    text: 'PyPlyne compiles to CPython AST in memory, so imports, objects, and tracebacks stay connected to normal Python.',
    href: '/docs/architecture',
  },
];

const installLinks = [
  {
    label: 'Package quickstart',
    href: '/docs/quickstart#install-pyplyne',
  },
  {
    label: 'Install VS Code extension',
    href: '/docs/editor#install-from-this-repository',
    iconSrc: '/img/editor-logos/vscode.svg',
    iconAlt: '',
  },
  {
    label: 'Install Neovim plugin',
    href: '/docs/editor#neovim',
    iconSrc: '/img/editor-logos/neovim.svg',
    iconAlt: '',
  },
];

const workflowSections = [
  {
    label: 'Write a pipeline file',
    title: 'Put the transformation in a .pyplyne script and run it once.',
    text: 'Start with the simplest workflow: write a pipeline file, import the Python helpers you already trust, then run it from the command line.',
    points: [
      'Use normal Python imports at the top of the file.',
      'Write one readable table or sequence pipeline.',
      'Run the script with the PyPlyne CLI.',
    ],
    href: '/docs/quickstart',
    linkLabel: 'Read the quickstart',
    language: 'pyplyne',
    code: `from pathlib import Path

sales = df read_csv(Path("sales.csv"))
summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total = sum(amount))

print(summary)
summary`,
    command: 'uv run pyplyne pipeline.pyplyne',
  },
  {
    label: 'Use it from Python',
    title: 'Run PyPlyne and get real Python objects back.',
    text: 'Run a short PyPlyne source string in one call, end it with the value you want, and read the live Polars DataFrame from the result.',
    points: [
      'Pass existing Python or Polars objects into the session.',
      'Use a one-shot run when you do not need persistent state.',
      'Use the source string\'s final expression as result.result.',
    ],
    href: '/docs/python-api',
    linkLabel: 'See the Python API',
    language: 'python',
    code: `import polars as pl
from pyplyne import run

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
print(summary)`,
  },
  {
    label: 'Explore from VS Code',
    title: 'Run blocks interactively while editing a normal pipeline file.',
    text: 'The local VS Code extension gives `.pyplyne` files syntax highlighting, block execution, diagnostics, and a persistent PyPlyne session.',
    points: [
      'Load data once, then run the block you are currently editing.',
      'Use the assignment command when you want to inspect the assigned value.',
      'Jump between blocks with the default editor keybindings.',
    ],
    href: '/docs/editor',
    linkLabel: 'Set up VS Code',
    language: 'pyplyne',
    code: `sales = df read_csv("sales.csv")

large_sales = sales
  |> where(amount > 100)
  |> select(region, amount)

large_sales`,
  },
  {
    label: 'Let agents iterate',
    title: 'Give AI agents a warm session for efficient data exploration.',
    text: 'Start a small session server, load big data once, then let an agent send focused snippets and inspect JSON responses without rerunning the full pipeline.',
    points: [
      'Keep large datasets and Python helpers resident in memory.',
      'Return structured feedback with result, diagnostic, and shape metadata.',
      'Refine transformations step by step over SSH or a local port.',
    ],
    href: '/docs/interactive-sessions#remote-or-agent-workflows',
    linkLabel: 'Read agent workflow docs',
    language: 'bash',
    code: `uv run pyplyne serve --port 8765 --load setup.pyplyne

uv run pyplyne send --json --expr 'sales'
uv run pyplyne send --json --expr '
df sales
  |> group_by(region)
  |> summarize(total = sum(amount))
'`,
  },
];

const tableInput = [
  {region: 'north', amount: 110},
  {region: 'south', amount: 165},
  {region: 'north', amount: 200},
  {region: 'west', amount: 70},
  {region: 'south', amount: 90},
  {region: 'west', amount: 120},
];

const tableCode = [
  'summary = df sales',
  '  |> group_by(region)',
  '  |> summarize(total = sum(amount))',
  '  |> arrange(total)',
];

const tableSteps = [
  {
    label: 'Start with the table named sales.',
    rows: tableInput,
    columns: ['region', 'amount'],
  },
  {
    label: 'Group the rows by region.',
    rows: [
      {region: 'north', amount: 110, group: 'A'},
      {region: 'north', amount: 200, group: 'A'},
      {region: 'south', amount: 165, group: 'B'},
      {region: 'south', amount: 90, group: 'B'},
      {region: 'west', amount: 70, group: 'C'},
      {region: 'west', amount: 120, group: 'C'},
    ],
    columns: ['region', 'amount'],
    groupColumn: 'group',
  },
  {
    label: 'Calculate total amount per group.',
    rows: [
      {region: 'north', total: 310, group: 'A'},
      {region: 'south', total: 255, group: 'B'},
      {region: 'west', total: 190, group: 'C'},
    ],
    columns: ['region', 'total'],
    groupColumn: 'group',
  },
  {
    label: 'Sort the summary by total.',
    rows: [
      {region: 'west', total: 190, group: 'C'},
      {region: 'south', total: 255, group: 'B'},
      {region: 'north', total: 310, group: 'A'},
    ],
    columns: ['region', 'total'],
    groupColumn: 'group',
  },
];

const sequenceInput = [
  {item: 'notebook', qty: 1},
  {item: 'coffee', qty: 3},
  {item: 'pens', qty: 2},
];

const sequenceCode = [
  'restock = seq orders',
  '  |> filter(qty > 1)',
  '  |> keep_fields(item)',
  '  |> set_fields(buy = item == "pens")',
];

const sequenceSteps = [
  {
    label: 'Start with a list of JSON-like order records.',
    value: sequenceInput,
  },
  {
    label: 'Keep records where qty is greater than one.',
    value: sequenceInput.filter((row) => row.qty > 1),
  },
  {
    label: 'Project each record down to the item field.',
    value: sequenceInput
      .filter((row) => row.qty > 1)
      .map((row) => ({item: row.item})),
  },
  {
    label: 'Flag records where item is pens.',
    value: sequenceInput
      .filter((row) => row.qty > 1)
      .map((row) => ({item: row.item, buy: row.item === 'pens'})),
  },
];

const inputColumns = {
  df: ['region', 'amount'],
  seq: ['item', 'qty'],
};

const dimRows = {
  df: null,
  seq: (row, step) => step >= 1 && row.qty <= 1,
};

function highlightedHtml(code, language) {
  const grammar = Prism.languages[language];
  if (!grammar) {
    return code;
  }
  return Prism.highlight(code, grammar, language);
}

function HighlightedPre({code, language}) {
  return (
    <pre>
      <code
        className={`language-${language}`}
        dangerouslySetInnerHTML={{__html: highlightedHtml(code, language)}}
      />
    </pre>
  );
}

function InstallPanel() {
  return (
    <section className={styles.installPanel} aria-label="Install PyPlyne">
      <div className={styles.installCommand}>
        <span>Install</span>
        <code>uv add "pyplyne @ git+https://github.com/pyplyne-org/pyplyne.git"</code>
      </div>
      <div className={styles.installCopy}>
        <p>Requires Python 3.13+. Use the Git source install until the PyPI package is published.</p>
        <nav className={styles.installLinks} aria-label="PyPlyne setup links">
          {installLinks.map((link) => (
            <Link to={link.href} key={link.href}>
              {link.iconSrc ? (
                <img src={link.iconSrc} alt={link.iconAlt} aria-hidden="true" />
              ) : null}
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </section>
  );
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = () => setPrefersReducedMotion(mediaQuery.matches);

    handleChange();
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      mediaQuery.addListener?.(handleChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        mediaQuery.removeListener?.(handleChange);
      }
    };
  }, []);

  return prefersReducedMotion;
}

function useCyclingStep(length, shouldCycle = true) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!shouldCycle || length <= 1) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setStep((current) => (current + 1) % length);
    }, 1900);
    return () => window.clearInterval(interval);
  }, [length, shouldCycle]);

  return step;
}

function DemoCode({lines, step}) {
  return (
    <pre className={styles.demoCode}>
      <code className="language-pyplyne">
        {lines.map((line, index) => (
          <span
            className={clsx(
              styles.codeLine,
              index === step && styles.activeCodeLine,
              index > step && styles.pendingCodeLine,
            )}
            key={line}
            dangerouslySetInnerHTML={{__html: highlightedHtml(line, 'pyplyne')}}
          />
        ))}
      </code>
    </pre>
  );
}

function MiniTable({columns, rows, dimRows, groupColumn}) {
  return (
    <div className={styles.miniTable} style={{'--columns': columns.length}}>
      <div className={styles.miniTableHead}>
        {columns.map((column) => (
          <span key={column}>{column}</span>
        ))}
      </div>
      {rows.map((row, index) => (
        <div
          className={clsx(
            styles.miniTableRow,
            groupColumn && styles.groupedTableRow,
            dimRows?.(row, index) && styles.dimmedDataRow,
          )}
          data-group={groupColumn ? row[groupColumn] : undefined}
          key={`${Object.values(row).join('-')}-${index}`}>
          {columns.map((column) => (
            <span key={column}>{String(row[column])}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

function RecordList({value, dimRows}) {
  return (
    <div className={styles.recordList}>
      {value.map((item, index) => (
        <div
          className={clsx(
            styles.recordRow,
            dimRows?.(item, index) && styles.dimmedDataRow,
          )}
          key={typeof item === 'string' ? `${item}-${index}` : `${Object.values(item).join('-')}-${index}`}>
          {typeof item === 'string' ? (
            <span className={styles.scalarValue}>{JSON.stringify(item)}</span>
          ) : (
            Object.entries(item).map(([key, entryValue]) => (
              <span className={styles.fieldPill} key={key}>
                <b>{key}</b> {JSON.stringify(entryValue)}
              </span>
            ))
          )}
        </div>
      ))}
    </div>
  );
}

function PipelineDemo({kind, title, subtitle, code, step, input, output}) {
  return (
    <article className={styles.preview}>
      <div className={styles.previewHeader}>
        <span>{title}</span>
        <span>{subtitle}</span>
      </div>
      <DemoCode lines={code} step={step} />
      <div className={styles.demoCaption}>
        {output.label}
      </div>
      <div className={styles.dataFlow}>
        <section className={styles.dataPanel}>
          <p>input</p>
          {kind === 'df' ? (
            <MiniTable
              columns={inputColumns[kind]}
              rows={input}
            />
          ) : (
            <RecordList
              value={input}
              dimRows={(row) => dimRows[kind]?.(row, step)}
            />
          )}
        </section>
        <section className={styles.dataPanel}>
          <p>output</p>
          {kind === 'df' ? (
            <MiniTable
              columns={output.columns}
              rows={output.rows}
              groupColumn={output.groupColumn}
            />
          ) : (
            <RecordList value={output.value} />
          )}
        </section>
      </div>
    </article>
  );
}

function HomepageHeader() {
  const prefersReducedMotion = usePrefersReducedMotion();
  const tableStep = useCyclingStep(tableSteps.length, !prefersReducedMotion);
  const sequenceStep = useCyclingStep(sequenceSteps.length, !prefersReducedMotion);
  const [activePreview, setActivePreview] = useState(0);
  const previewStackRef = useRef(null);
  const demos = [
    {
      kind: 'df',
      title: 'tables.pyplyne',
      subtitle: 'df pipeline',
      code: tableCode,
      step: tableStep,
      input: tableInput,
      output: tableSteps[tableStep],
    },
    {
      kind: 'seq',
      title: 'records.pyplyne',
      subtitle: 'seq pipeline',
      code: sequenceCode,
      step: sequenceStep,
      input: sequenceInput,
      output: sequenceSteps[sequenceStep],
    },
  ];
  const demoCount = demos.length;

  const showPreview = useCallback(
    (index) => {
      const nextIndex = (index + demoCount) % demoCount;
      setActivePreview(nextIndex);

      const nextPreview = previewStackRef.current?.children[nextIndex];
      nextPreview?.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'nearest',
        inline: 'start',
      });
    },
    [demoCount, prefersReducedMotion],
  );

  const handlePreviewScroll = useCallback(() => {
    const stack = previewStackRef.current;
    if (!stack) {
      return;
    }

    const stackLeft = stack.getBoundingClientRect().left;
    let closestIndex = 0;
    let closestDistance = Infinity;

    Array.from(stack.children).forEach((child, index) => {
      const distance = Math.abs(child.getBoundingClientRect().left - stackLeft);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });

    setActivePreview(closestIndex);
  }, []);

  const handlePreviewKeyDown = useCallback(
    (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        showPreview(activePreview - 1);
      }

      if (event.key === 'ArrowRight') {
        event.preventDefault();
        showPreview(activePreview + 1);
      }
    },
    [activePreview, showPreview],
  );

  return (
    <header className={styles.hero}>
      <div className={styles.heroInner}>
        <section className={styles.heroCopy}>
          <div className={styles.brandLockup}>
            <h1>PyPlyne</h1>
            <p className={styles.kicker}>Clean functional pipes, directly in Python</p>
          </div>
          <p className={styles.lede}>
            Write data transformations left to right for Polars tables and
            JSON-like records, without leaving Python.
          </p>
          <div className={styles.actions}>
            <Link className="button button--primary" to="/docs/language-guide">
              Read the guide
            </Link>
            <Link className="button button--secondary" to="/docs/reference">
              Open reference
            </Link>
          </div>
        </section>
        <InstallPanel />
        <section className={styles.previewCarousel} aria-label="PyPlyne syntax examples">
          <div
            className={styles.previewStack}
            ref={previewStackRef}
            onKeyDown={handlePreviewKeyDown}
            onScroll={handlePreviewScroll}
            role="region"
            aria-label="Scrollable syntax examples"
            tabIndex={0}>
            {demos.map((demo) => (
              <PipelineDemo
                key={demo.kind}
                kind={demo.kind}
                title={demo.title}
                subtitle={demo.subtitle}
                code={demo.code}
                step={demo.step}
                input={demo.input}
                output={demo.output}
              />
            ))}
          </div>
          <div className={styles.previewControls} aria-label="Select syntax example">
            <button
              className={styles.previewControlButton}
              type="button"
              onClick={() => showPreview(activePreview - 1)}
              aria-label="Show previous syntax example">
              Prev
            </button>
            <div className={styles.previewIndicators}>
              {demos.map((demo, index) => (
                <button
                  className={clsx(
                    styles.previewIndicator,
                    activePreview === index && styles.activePreviewIndicator,
                  )}
                  type="button"
                  onClick={() => showPreview(index)}
                  aria-current={activePreview === index ? 'true' : undefined}
                  aria-label={`Show ${demo.title} example`}
                  key={demo.kind}
                />
              ))}
            </div>
            <button
              className={styles.previewControlButton}
              type="button"
              onClick={() => showPreview(activePreview + 1)}
              aria-label="Show next syntax example">
              Next
            </button>
          </div>
        </section>
      </div>
    </header>
  );
}

export default function Home() {
  return (
    <Layout
      title="PyPlyne"
      description="Clean functional pipes for Python data transformations.">
      <HomepageHeader />
      <main>
        <section className={styles.featureBand}>
          <div className={styles.sectionIntro}>
            <p className={styles.sectionLabel}>What it gives you</p>
            <h2>A readable layer over everyday data work.</h2>
          </div>
          <div className={styles.featureGrid}>
            {features.map((feature) => (
              <Link
                className={clsx(styles.featureCard)}
                to={feature.href}
                key={feature.title}>
                <p className={styles.featureLabel}>{feature.label}</p>
                <h2>{feature.title}</h2>
                <p>{feature.text}</p>
              </Link>
            ))}
          </div>
        </section>
        <section className={styles.benefitBand}>
          <div className={styles.sectionIntro}>
            <p className={styles.sectionLabel}>Run it your way</p>
            <h2>Run it once, embed it in Python, or keep a live session warm.</h2>
          </div>
          <div className={styles.benefitStack}>
            {workflowSections.map((workflow) => (
              <article className={styles.benefitSection} key={workflow.title}>
                <div className={styles.benefitCopy}>
                  <p className={styles.benefitLabel}>{workflow.label}</p>
                  <h3>{workflow.title}</h3>
                  <p>{workflow.text}</p>
                  <ul>
                    {workflow.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                  <Link className={styles.textLink} to={workflow.href}>
                    {workflow.linkLabel}
                  </Link>
                </div>
                <div className={styles.workflowCodeStack}>
                  <HighlightedPre
                    code={workflow.code}
                    language={workflow.language}
                  />
                  {workflow.command ? (
                    <HighlightedPre
                      code={workflow.command}
                      language="bash"
                    />
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}
