---
title: Interactive Sessions
description: Persistent REPL, session server, pyplyne send, and agent-facing workflows.
---

# Interactive Sessions

PyPlyne sessions keep Python imports, loaded data, intermediate variables, and
`seq`/`df` shape information alive between snippets. They are useful when
loading data is slow and transformation work is iterative.

Use the terminal REPL when a human is typing and wants immediate feedback. Use
the session server plus `pyplyne send` when an editor, script, or agent needs to
send small snippets into the same warm execution environment.

## Terminal REPL

Start a REPL:

```bash
uv run pyplyne repl
```

Load one or more setup files before the prompt appears:

```bash
uv run pyplyne repl --load imports.pyplyne --load data.pyplyne
```

Example:

```pyplyne
pyplyne> numbers = seq [1, 2, 3]

pyplyne> numbers |> map(_ * 10)
[10, 20, 30]
```

The REPL runs complete snippets as they are entered. A single-line expression
runs immediately. A simple assignment block can continue across lines; finish it
with a blank line. Use `:paste` when you already have a multi-line snippet on
the clipboard.

Useful commands:

| Command | Purpose |
| --- | --- |
| `:help` | Show REPL help. |
| `:vars` | Show names currently available in the session. |
| `:shapes` | Show known `seq`/`df` shapes, including `_` when the last result is shaped. |
| `:paste` | Enter paste mode for a multi-line snippet. |
| `:quit` | Exit. |

Use `:paste` for multi-line snippets. End the pasted block with a single `.`
on its own line.

## Session Server

Start a local HTTP session and leave that process running:

```bash
uv run pyplyne serve --port 8765
```

Preload setup files before the server accepts snippets. Repeat `--load` for
multiple files:

```bash
uv run pyplyne serve --port 8765 --load imports.pyplyne --load data.pyplyne
```

The server listens on `127.0.0.1` by default. Bind an explicit host when you are
using containers, SSH forwarding, or a remote development machine:

```bash
uv run pyplyne serve --host 0.0.0.0 --port 8765
```

The HTTP surface is intentionally small:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check that the server is running. |
| `GET /shapes` | Return the current shape table as JSON. |
| `POST /run` | Run PyPlyne source in the persistent session. |

The server does not add authentication. Keep it bound to localhost, use SSH
port forwarding, or put it behind trusted infrastructure before exposing it
beyond your machine.

## Send Snippets

Send snippets into the same live session:

```bash
uv run pyplyne send --expr 'numbers = seq [1, 2, 3]'
uv run pyplyne send --expr 'numbers |> map(_ * 10)'
```

Send a file when the source is easier to maintain on disk:

```bash
uv run pyplyne send --file snippet.pyplyne
```

`pyplyne send` also reads from stdin:

```bash
echo 'numbers |> filter(_ > 1)' | uv run pyplyne send
```

By default, `send` targets the session base URL `http://127.0.0.1:8765` and
posts to `/run`. Override the base URL with a specific port, `--url`, or
`PYPLYNE_URL`; the client appends `/run` unless the URL already ends there:

```bash
uv run pyplyne send --port 9000 --expr 'numbers'
uv run pyplyne send --url http://127.0.0.1:9000 --expr 'numbers'
uv run pyplyne send --url http://127.0.0.1:9000/run --expr 'numbers'
PYPLYNE_URL=http://127.0.0.1:9000 uv run pyplyne send --expr 'numbers'
```

Use `--filename` for piped or expression source when you want diagnostics to
point at a stable virtual filename:

```bash
uv run pyplyne send --filename agent-step-03.pyplyne --expr 'numbers |> map(_ + missing)'
```

Use `--timeout` to change the client request timeout from the default 30
seconds:

```bash
uv run pyplyne send --timeout 120 --file slow-snippet.pyplyne
```

`pyplyne send` exits with status `0` for 2xx HTTP responses and `1` for non-2xx
HTTP responses. Successful response bodies are written to stdout; error
response bodies are written to stderr. Network failures and timeouts are raised
by the client process.

## JSON Output

Ask for JSON when an agent, editor, or script is consuming the response:

```bash
uv run pyplyne send --expr 'numbers |> map(_ * 10)' --json
```

Text responses are for humans. JSON responses are for tools that need to branch
on status, inspect streams, preserve diagnostics, or keep track of shape
information without parsing terminal formatting.

Successful JSON responses include the same session state that text output uses:

```json
{
  "ok": true,
  "filename": "<pyplyne-session:2>",
  "stdout": "",
  "stderr": "",
  "result": "[10, 20, 30]",
  "error": null,
  "phase": null,
  "traceback": "",
  "diagnostic": null,
  "shapes": {
    "_": "seq",
    "numbers": "seq"
  }
}
```

The `result` field is a formatted string representation of the value, not a
lossless JSON serialization of every Python object. Use it for display,
inspection, and lightweight agent feedback. Keep durable data in named session
variables or write it with PyPlyne/Python helpers.

## Remote Or Agent Workflows

The server binds to a host and port, so it can be used over SSH port
forwarding:

```bash
ssh -L 8765:127.0.0.1:8765 user@remote
PYPLYNE_URL=http://127.0.0.1:8765 uv run pyplyne send --expr 'sales'
```

This gives agents and editor integrations a simple loop:

1. Start or connect to a session.
2. Load imports, helpers, and data once with `--load` or an initial snippet.
3. Send complete, focused PyPlyne snippets.
4. Request `--json` and inspect `ok`, `result`, `diagnostic`, and `shapes`.
5. Use `--filename` so parse, compile, and runtime messages point back to the
   agent step or editor buffer.
6. Refine the pipeline without rebuilding the whole environment.

Prefer complete snippets over fragments that depend on client-side context. The
session persists names and shapes, but each request still compiles as its own
PyPlyne source unit.

## Last Result

Expression snippets store their final expression result as `_`, following the
Python and IPython REPL convention:

```pyplyne
numbers |> map(_ * 10)
_ |> filter(_ > 10)
```

In the second line, the left `_` is the previous session result and the right
`_` is the current item inside `filter`.

Assignments and imports do not replace `_` unless the snippet ends with an
expression. For example, `numbers = seq [1, 2, 3]` stores `numbers` but leaves
the previous `_` value alone.

The session stores `_` as a normal value for the last expression result. It
tracks shape information for `_` only when that result is sequence-shaped or
table-shaped:

```text
pyplyne> numbers |> map(_ * 10)
[10, 20, 30]
pyplyne> :shapes
{'numbers': 'seq', '_': 'seq'}

pyplyne> 42
42
pyplyne> :shapes
{'numbers': 'seq'}
```

After the first expression, `_` is shaped as `seq`. After the scalar expression,
`_` is still the value `42`, but the `_` shape is cleared so shape-specific
verbs cannot accidentally run against stale shape information.

Inside sequence verbs, `_` is the current item placeholder. At the start of a
pipeline, `_` is the previous session result. PyPlyne uses syntax to distinguish
those roles:

```pyplyne
_ |> filter(_ > 10)
```

The left `_` is read from the session. The right `_` is scoped to the
`filter(...)` callback. Use numbered placeholders such as `_1` and `_2` for
multi-argument callbacks, but do not mix `_` with numbered placeholders in the
same callback expression.

## Error Messages

Interactive sessions show focused diagnostics instead of internal Python stack
traces. Messages include:

- the phase where the problem happened: `parse`, `compile`, or `runtime`
- the error type and message
- the PyPlyne source line and caret when available
- a short hint for common shape, verb, and table errors

Example:

```text
compile error: SyntaxError: where is a df verb, but the current pipeline is seq
 --> <pyplyne-session:2>:1:15
  |
1 | rows |> where(amount > 0)
  |               ^
hint: Use to_table() before df verbs, or start the source with df if it is table-shaped.
```

JSON error responses include a structured `diagnostic` object:

```json
{
  "phase": "runtime",
  "error_type": "TypeError",
  "message": "seq annotation expects iterable data, got int",
  "filename": "<pyplyne-session:3>",
  "line": 1,
  "column": 16,
  "source": "nonsense = seq 42",
  "caret": "               ^",
  "hint": "Use seq with iterable values, or wrap a scalar in [...] for a one-item sequence.",
  "display": "runtime error: TypeError: seq annotation expects iterable data, got int\n --> <pyplyne-session:3>:1:16\n  |\n1 | nonsense = seq 42\n  |                ^\nhint: Use seq with iterable values, or wrap a scalar in [...] for a one-item sequence."
}
```

JSON error responses also include `ok: false`, `stdout`, `stderr`, `phase`,
`error`, `traceback`, and `shapes`. Failed `/run` requests use a non-2xx HTTP
status, so clients should read the response body even when their HTTP library
raises an error. The full traceback is kept in JSON output and on the execution
result for deeper debugging, while the human text path shows the focused
diagnostic first.
