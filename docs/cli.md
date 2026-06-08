---
title: CLI Reference
description: Commands for running scripts, starting sessions, and sending snippets.
---

# CLI Reference

PyPlyne installs one command:

```bash
pyplyne
```

When working from this repository, run the same command through `uv`:

```bash
uv run pyplyne ...
```

This page explains the CLI workflows. For the exact current usage strings and
flag list, see [Generated CLI Help](generated-cli-reference).

## Choose A Command

| Goal | Command |
| --- | --- |
| Run a `.pyplyne` file once | `pyplyne run SCRIPT` or `pyplyne SCRIPT` |
| Explore in a terminal | `pyplyne repl` |
| Keep a session alive over HTTP | `pyplyne serve` |
| Send source to that HTTP session | `pyplyne send` |

## Run A Script Once

Use `run` for batch-style work: examples, checked-in scripts, and pipelines you
expect to execute from a shell or job runner.

```bash
uv run pyplyne run examples/list_pipeline.pyplyne
```

The command form is intentionally optional for scripts, so this is equivalent:

```bash
uv run pyplyne examples/list_pipeline.pyplyne
```

Each run starts a fresh PyPlyne runtime. Use an interactive session when you want
imports, loaded data, variables, and shape information to survive across
snippets.

## Work In A Terminal REPL

Use the REPL when you are exploring by hand and want immediate feedback without
starting a separate server process.

```bash
uv run pyplyne repl
```

Load one or more setup files before the prompt appears:

```bash
uv run pyplyne repl --load imports.pyplyne --load data.pyplyne
```

The REPL shares the same session model as the HTTP server, so variables and the
last result remain available as you iterate. See [Interactive Sessions](interactive-sessions.md)
for REPL commands such as `:vars`, `:paste`, and `:quit`.

## Keep A Session Warm

Use `serve` when another process needs to evaluate PyPlyne snippets against the
same live state. This is useful for editor integrations, coding agents, and
data exploration where loading the data once is cheaper than rerunning the
whole script after every change.

```bash
uv run pyplyne serve --port 8765
```

The server listens locally by default. Bind an explicit host when you are using
port forwarding, containers, or another environment where `127.0.0.1` is not
the right interface:

```bash
uv run pyplyne serve --host 0.0.0.0 --port 8765
```

Preload one or more files to establish imports, helper functions, or shared
data before the server accepts snippets. Repeat `--load` for multiple files:

```bash
uv run pyplyne serve --port 8765 --load imports.pyplyne --load data.pyplyne
```

## Send Source To A Session

Use `send` after a `serve` process is running. Send a single expression when
you are iterating from the shell:

```bash
uv run pyplyne send --expr 'numbers = seq [1, 2, 3]'
uv run pyplyne send --expr 'numbers |> map(_ * 10)'
```

Send a file when the snippet is easier to maintain on disk:

```bash
uv run pyplyne send --file snippet.pyplyne
```

Or pipe source through stdin:

```bash
echo 'numbers |> filter(_ > 10)' | uv run pyplyne send
```

By default, `send` targets the session base URL `http://127.0.0.1:8765` and
posts to `/run`. Override the base URL with a specific port, `--url`, or
`PYPLYNE_URL`; the client appends `/run` unless the URL already ends there:

```bash
uv run pyplyne send --port 9000 --expr 'numbers'
PYPLYNE_URL=http://127.0.0.1:9000 uv run pyplyne send --expr 'numbers'
```

Request JSON when another tool needs structured output or diagnostics:

```bash
uv run pyplyne send --expr 'numbers |> map(_ + 1)' --json
```

Text responses are meant for humans. JSON responses are meant for scripts,
editors, and agents that need to inspect success, values, and diagnostic
fields without parsing terminal formatting.

`pyplyne send` exits with status `0` for 2xx HTTP responses and `1` for non-2xx
HTTP responses. Network failures and timeouts are raised by the client process.

## Diagnostics

PyPlyne reports parse, compile, and runtime errors with source locations when it
can. Text output shows the readable diagnostic. JSON output includes a
`diagnostic` object with the same information in fields such as `phase`,
`error_type`, `message`, `filename`, `line`, `column`, `source`, `caret`,
`hint`, and `display`.

If you do not pass a source name, PyPlyne uses a generated session label in
diagnostics. Optionally use `--source-name` with piped, generated, or expression
source when you want diagnostics to refer to a stable virtual source name
instead. This names the submitted snippet for diagnostics; it does not read a
file. `--filename` is accepted as a compatibility alias.

In session examples, `_` may mean either the last expression result or the
current item inside a sequence callback. See [Last Result](interactive-sessions.md#last-result)
for the distinction.

## Exact Help

The generated reference mirrors the current CLI implementation and is the
right place to check exact arguments, defaults, and option names:

- [Generated CLI Help](generated-cli-reference)
