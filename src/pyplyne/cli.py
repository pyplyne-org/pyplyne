from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import CodeType
from typing import Any

from pyplyne.client import DEFAULT_HOST, DEFAULT_PORT, send_source
from pyplyne.parser import parse_source
from pyplyne.runtime import runtime_globals
from pyplyne.session import PyPlyneSession, create_session_server
from pyplyne.transformer import compile_ast


def compile_source(
    source: str,
    filename: str = "<pyplyne>",
    symbol_kinds: dict[str, str] | None = None,
) -> CodeType:
    tree = parse_source(source, filename=filename)
    module = compile_ast(tree, filename=filename, symbol_kinds=symbol_kinds)
    return compile(module, filename=filename, mode="exec")


def run_source(
    source: str,
    filename: str = "<pyplyne>",
    globals_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    env = runtime_globals()
    if globals_dict:
        env.update(globals_dict)
    env["__file__"] = filename
    code = compile_source(source, filename=filename)
    exec(code, env)
    return env


def run_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    return run_source(file_path.read_text(encoding="utf-8"), filename=str(file_path))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"run", "repl", "serve", "send"}:
        command = argv.pop(0)
        if command == "run":
            return _run_command(argv)
        if command == "repl":
            return _repl_command(argv)
        if command == "serve":
            return _serve_command(argv)
        return _send_command(argv)
    return _run_command(argv)


def _run_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplyne run", description="Run a PyPlyne script."
    )
    parser.add_argument("script", help="Path to a .pyplyne script")
    args = parser.parse_args(argv)

    try:
        run_file(args.script)
    except Exception:
        raise
    return 0


def _repl_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplyne repl", description="Start a persistent PyPlyne REPL."
    )
    parser.add_argument(
        "--load",
        action="append",
        default=[],
        help="Run a .pyplyne file before starting the REPL. Can be used more than once",
    )
    args = parser.parse_args(argv)

    from pyplyne.repl import run_repl

    session = PyPlyneSession()
    for path in args.load:
        session.load_file(path)
    return run_repl(session)


def _serve_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplyne serve", description="Start a persistent PyPlyne HTTP session."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    parser.add_argument(
        "--load",
        action="append",
        default=[],
        help="Run a .pyplyne file before serving. Can be used more than once",
    )
    args = parser.parse_args(argv)

    session = PyPlyneSession()
    for path in args.load:
        session.load_file(path)
    server = create_session_server(args.host, args.port, session=session)
    host, port = server.server_address
    print(f"PyPlyne session server listening on http://{host}:{port}/run", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


def _send_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplyne send", description="Send PyPlyne source to a persistent session."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--expr", help="PyPlyne source to send")
    source.add_argument("--file", help="Read PyPlyne source from a file")
    parser.add_argument(
        "--url",
        help="Session server URL. Defaults to PYPLYNE_URL or http://127.0.0.1:8765",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host to use when --url and PYPLYNE_URL are unset",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Port to use when --url and PYPLYNE_URL are unset",
    )
    parser.add_argument(
        "--json", action="store_true", help="Request structured JSON output"
    )
    parser.add_argument(
        "--source-name",
        "--filename",
        dest="filename",
        help="Virtual source name to use in session diagnostics and tracebacks",
    )
    parser.add_argument(
        "--timeout", type=float, default=30, help="Request timeout in seconds"
    )
    args = parser.parse_args(argv)

    if args.expr is not None:
        source_text = args.expr if args.expr.endswith("\n") else args.expr + "\n"
        filename = args.filename
    elif args.file is not None:
        path = Path(args.file)
        source_text = path.read_text(encoding="utf-8")
        filename = args.filename or str(path)
    else:
        source_text = sys.stdin.read()
        filename = args.filename

    response = send_source(
        source_text,
        url=args.url,
        host=args.host,
        port=args.port,
        json_output=args.json,
        filename=filename,
        timeout=args.timeout,
    )
    stream = sys.stdout if response.ok else sys.stderr
    stream.write(response.body)
    if response.body and not response.body.endswith("\n"):
        stream.write("\n")
    return 0 if response.ok else 1


if __name__ == "__main__":
    sys.exit(main())
