---
title: Generated CLI Help
description: Command help generated from the current PyPlyne CLI implementation.
---

# Generated CLI Help

This page is generated from the current `pyplyne` command implementation.
Update the CLI code first, then regenerate with `npm run docs:cli` from
`site/`.

## Commands

| Command | Purpose |
| --- | --- |
| `pyplyne run SCRIPT` | Run a `.pyplyne` file. |
| `pyplyne repl` | Start a persistent terminal REPL. |
| `pyplyne serve` | Start a persistent HTTP session. |
| `pyplyne send` | Send source to a session server. |

The hand-written [CLI Reference](cli) includes examples and the `pyplyne SCRIPT`
shorthand. The sections below are exact help snapshots from the explicit
subcommands.

## Run

```text title="pyplyne run --help"
usage: pyplyne run [-h] script

Run a PyPlyne script.

positional arguments:
  script      Path to a .pyplyne script

options:
  -h, --help  show this help message and exit
```

## REPL

```text title="pyplyne repl --help"
usage: pyplyne repl [-h] [--load LOAD]

Start a persistent PyPlyne REPL.

options:
  -h, --help   show this help message and exit
  --load LOAD  Run a .pyplyne file before starting the REPL. Can be used more
               than once
```

## Serve

```text title="pyplyne serve --help"
usage: pyplyne serve [-h] [--host HOST] [--port PORT] [--load LOAD]

Start a persistent PyPlyne HTTP session.

options:
  -h, --help   show this help message and exit
  --host HOST  Host to bind
  --port PORT  Port to bind
  --load LOAD  Run a .pyplyne file before serving. Can be used more than once
```

## Send

```text title="pyplyne send --help"
usage: pyplyne send [-h] [--expr EXPR | --file FILE] [--url URL] [--host HOST]
                    [--port PORT] [--json] [--source-name FILENAME]
                    [--timeout TIMEOUT]

Send PyPlyne source to a persistent session.

options:
  -h, --help            show this help message and exit
  --expr EXPR           PyPlyne source to send
  --file FILE           Read PyPlyne source from a file
  --url URL             Session server URL. Defaults to PYPLYNE_URL or
                        http://127.0.0.1:8765
  --host HOST           Host to use when --url and PYPLYNE_URL are unset
  --port PORT           Port to use when --url and PYPLYNE_URL are unset
  --json                Request structured JSON output
  --source-name, --filename FILENAME
                        Virtual source name to use in session diagnostics and
                        tracebacks
  --timeout TIMEOUT     Request timeout in seconds
```
