from __future__ import annotations

import ast
import contextlib
import io
import json
import linecache
import pprint
import threading
import traceback
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import CodeType
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import polars as pl

from pyplyne.diagnostics import build_diagnostic
from pyplyne.parser import parse_source
from pyplyne.runtime import runtime_globals
from pyplyne.transformer import DF_KIND, SEQ_KIND, compile_ast


class _MissingDefault:
    def __repr__(self) -> str:
        return "MISSING"


_MISSING = _MissingDefault()


def run(
    source: str,
    context: Optional[dict[str, Any]] = None,
    filename: str = "<pyplyne>",
    *,
    capture_output: bool = True,
    raise_on_error: bool = True,
    store_result: bool = True,
) -> PyPlyneExecutionResult:
    """Run PyPlyne source once without managing a persistent session.

    Args:
        source: PyPlyne source code to execute.
        context: Optional Python names and values available to the source.
        filename: Virtual filename used in diagnostics.
        capture_output: Capture stdout/stderr into the result object. When
            false, output goes to the process streams and the result stream
            fields are empty.
        raise_on_error: Raise failures instead of returning a non-ok result.
        store_result: Capture the final expression result.

    Returns:
        PyPlyneExecutionResult: Captured output, result value, shapes, and any
        non-raised error from the one-shot run.
    """

    session = PyPlyneSession(context)
    return session.run(
        source,
        filename=filename,
        capture_output=capture_output,
        raise_on_error=raise_on_error,
        store_result=store_result,
    )


def run_file(
    path: str | Path,
    context: Optional[dict[str, Any]] = None,
    *,
    capture_output: bool = True,
    raise_on_error: bool = True,
    store_result: bool = True,
) -> PyPlyneExecutionResult:
    """Run a `.pyplyne` file once without managing a persistent session.

    Args:
        path: Path to the `.pyplyne` source file.
        context: Optional Python names and values available to the file.
        capture_output: Capture stdout/stderr into the result object. When
            false, output goes to the process streams and the result stream
            fields are empty.
        raise_on_error: Raise failures instead of returning a non-ok result.
        store_result: Capture the final expression result.

    Returns:
        PyPlyneExecutionResult: Captured output, result value, shapes, and any
        non-raised error from the one-shot file run.
    """

    file_path = Path(path)
    return run(
        file_path.read_text(encoding="utf-8"),
        context=context,
        filename=str(file_path),
        capture_output=capture_output,
        raise_on_error=raise_on_error,
        store_result=store_result,
    )


@dataclass(frozen=True)
class PyPlyneExecutionResult:
    """Result object returned by `PyPlyneSession.run`.

    `ok` is true when execution completed without an error. When `ok` is false,
    `phase`, `error`, `traceback`, and `stderr` describe what failed.

    Attributes:
        filename: Virtual filename used for diagnostics and tracebacks.
        stdout: Text written to standard output while the source ran.
        stderr: Text written to standard error while the source ran.
        result: Final expression value when `store_result` is true and the
            snippet ends with an expression.
        error: Exception captured from parsing, compiling, or running the source.
        phase: Failure phase, usually `parse`, `compile`, or `runtime`.
        traceback: Python traceback text for captured errors.
        shapes: Known `df` and `seq` variable shapes after the run.
    """

    filename: str
    stdout: str
    stderr: str
    result: Any = None
    error: Optional[BaseException] = None
    phase: Optional[str] = None
    traceback: str = ""
    shapes: Optional[dict[str, str]] = None

    @property
    def ok(self) -> bool:
        """Whether the run completed without a captured error."""

        return self.error is None


class PyPlyneSession:
    """Persistent PyPlyne execution environment.

    A session keeps Python globals, imports, runtime helpers, known `df`/`seq`
    shapes, and the most recent expression result across runs.
    """

    def __init__(self, globals_dict: Optional[dict[str, Any]] = None) -> None:
        """Create a session seeded with optional Python globals.

        Args:
            globals_dict: Initial names and values to add to the session
                environment.
        """

        self.env = runtime_globals()
        if globals_dict:
            self.env.update(globals_dict)
        self.symbol_kinds: dict[str, str] = {}
        self._run_count = 0
        self._lock = threading.RLock()

    def run(
        self,
        source: str,
        filename: Optional[str] = None,
        *,
        capture_output: bool = True,
        raise_on_error: bool = True,
        store_result: bool = True,
    ) -> PyPlyneExecutionResult:
        """Compile and execute PyPlyne source in this persistent session.

        Args:
            source: PyPlyne source code to execute.
            filename: Optional virtual filename used in diagnostics.
            capture_output: Capture stdout/stderr into the result object. When
                false, output goes to the process streams and the result stream
                fields are empty.
            raise_on_error: Raise failures instead of returning a non-ok result.
            store_result: Capture the final expression result and store it as
                `_`. Assignment-only snippets do not replace `_`.

        Returns:
            PyPlyneExecutionResult: Captured output, result value, shapes, and any
            non-raised error.

        Raises:
            Exception: Re-raises parse, compile, or runtime failures when
            `raise_on_error` is true.
        """

        with self._lock:
            return self._run_locked(
                source,
                filename=filename,
                capture_output=capture_output,
                raise_on_error=raise_on_error,
                store_result=store_result,
            )

    def _run_locked(
        self,
        source: str,
        filename: Optional[str],
        *,
        capture_output: bool,
        raise_on_error: bool,
        store_result: bool,
    ) -> PyPlyneExecutionResult:
        self._run_count += 1
        filename = filename or f"<pyplyne-session:{self._run_count}>"
        self.env["__file__"] = filename
        self._register_source(filename, source)

        stdout = io.StringIO()
        stderr = io.StringIO()
        old_shapes = self.symbol_kinds.copy()
        next_shapes = self.symbol_kinds.copy()
        result = None
        error = None
        phase = None
        traceback_text = ""
        current_phase = "compile"

        try:
            code = self._compile(source, filename, next_shapes, store_result=store_result)
            current_phase = "runtime"
            with self._output_context(stdout, stderr, capture_output):
                exec(code, self.env)
            self.symbol_kinds = next_shapes
            if store_result and "__pyplyne_last_result__" in self.env:
                result = self.env.pop("__pyplyne_last_result__")
                self.env["_"] = result
                result_kind = self._shape_from_value(result)
                if result_kind:
                    self.symbol_kinds["_"] = result_kind
                else:
                    self.symbol_kinds.pop("_", None)
        except Exception as exc:
            error = exc
            phase = getattr(exc, "phase", current_phase)
            traceback_text = traceback.format_exc()
            self.symbol_kinds = self._shapes_for_existing_values(old_shapes, next_shapes)
            self.env.pop("__pyplyne_last_result__", None)
            if raise_on_error:
                raise

        return PyPlyneExecutionResult(
            filename=filename,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            result=result,
            error=error,
            phase=phase,
            traceback=traceback_text,
            shapes=self.symbol_kinds.copy(),
        )

    def load_file(self, path: str) -> PyPlyneExecutionResult:
        """Run a `.pyplyne` file inside this session.

        `load_file` uses the default `run` behavior, including raising on
        errors. Read the file and call `run(..., raise_on_error=False)` when
        non-raising file execution is needed.

        Args:
            path: Path to the `.pyplyne` source file.

        Returns:
            PyPlyneExecutionResult: Result from running the file contents.
        """

        with open(path, encoding="utf-8") as handle:
            return self.run(handle.read(), filename=path)

    def get(self, name: str, default: Any = _MISSING) -> Any:
        """Return a named value from the session environment.

        Args:
            name: Name to read from the session.
            default: Optional fallback returned when the name is missing.

        Returns:
            Any: The live Python object stored in the session.

        Raises:
            KeyError: If the name is missing and no default was supplied.
        """

        if name in self.env:
            return self.env[name]
        if default is not _MISSING:
            return default
        raise KeyError(f"PyPlyne session has no value named {name!r}")

    def get_df(self, name: str) -> pl.DataFrame:
        """Return a named value as a Polars DataFrame.

        Args:
            name: Name to read from the session.

        Returns:
            polars.DataFrame: The live DataFrame stored in the session.

        Raises:
            KeyError: If the name is missing.
            TypeError: If the named value is not a Polars DataFrame.
        """

        value = self.get(name)
        if isinstance(value, pl.DataFrame):
            return value
        raise TypeError(
            f"PyPlyne session value {name!r} is not a Polars DataFrame "
            f"(got {type(value).__name__})"
        )

    def get_seq(self, name: str) -> list[Any] | tuple[Any, ...]:
        """Return a named value as a sequence.

        Args:
            name: Name to read from the session.

        Returns:
            list | tuple: The live sequence stored in the session.

        Raises:
            KeyError: If the name is missing.
            TypeError: If the named value is not a list or tuple.
        """

        value = self.get(name)
        if isinstance(value, (list, tuple)):
            return value
        raise TypeError(
            f"PyPlyne session value {name!r} is not a sequence "
            f"(got {type(value).__name__})"
        )

    def _compile(
        self,
        source: str,
        filename: str,
        symbol_kinds: dict[str, str],
        *,
        store_result: bool,
    ) -> CodeType:
        tree = parse_source(source, filename=filename)
        module = compile_ast(tree, filename=filename, symbol_kinds=symbol_kinds)
        if store_result:
            self._capture_last_expression(module)
        ast.fix_missing_locations(module)
        return compile(module, filename=filename, mode="exec")

    def _capture_last_expression(self, module: ast.Module) -> None:
        if not module.body or not isinstance(module.body[-1], ast.Expr):
            return

        expression = module.body[-1]
        target = ast.Name(id="__pyplyne_last_result__", ctx=ast.Store())
        ast.copy_location(target, expression)
        assignment = ast.Assign(targets=[target], value=expression.value)
        ast.copy_location(assignment, expression)
        module.body[-1] = assignment

    def _register_source(self, filename: str, source: str) -> None:
        lines = source.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        linecache.cache[filename] = (len(source), None, lines, filename)

    @contextlib.contextmanager
    def _output_context(
        self,
        stdout: io.StringIO,
        stderr: io.StringIO,
        capture_output: bool,
    ):
        if not capture_output:
            yield
            return
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            yield

    def _shape_from_value(self, value: Any) -> Optional[str]:
        if isinstance(value, (pl.DataFrame, pl.LazyFrame)):
            return DF_KIND
        if isinstance(value, (list, tuple)):
            return SEQ_KIND
        return None

    def _shapes_for_existing_values(
        self,
        old_shapes: dict[str, str],
        next_shapes: dict[str, str],
    ) -> dict[str, str]:
        shapes = old_shapes.copy()
        for name, kind in next_shapes.items():
            if name in self.env:
                shapes[name] = kind
        return shapes


class PyPlyneHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], session: Optional[PyPlyneSession] = None) -> None:
        super().__init__(server_address, PyPlyneRequestHandler)
        self.session = session or PyPlyneSession()


class PyPlyneRequestHandler(BaseHTTPRequestHandler):
    server: PyPlyneHTTPServer

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/health"):
            self._send_text(200, "pyplyne session server is running\n")
            return
        if self.path.startswith("/shapes"):
            self._send_json(200, self.server.session.symbol_kinds)
            return
        self._send_text(404, "not found\n")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/run":
            self._send_text(404, "not found\n")
            return

        length = int(self.headers.get("Content-Length", "0"))
        source = self.rfile.read(length).decode("utf-8")
        params = parse_qs(parsed.query)
        filename = params.get("filename", [None])[0]
        wants_json = (
            params.get("format", [""])[0] == "json"
            or "application/json" in self.headers.get("Accept", "")
        )
        result = self.server.session.run(source, filename=filename, raise_on_error=False)
        status = 200 if result.ok else 500
        if wants_json:
            self._send_json(status, self._json_payload(result))
            return
        self._send_text(status, self._text_payload(result))

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json_payload(self, result: PyPlyneExecutionResult) -> dict[str, Any]:
        diagnostic = build_diagnostic(result)
        return {
            "ok": result.ok,
            "filename": result.filename,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "result": self._format_value(result.result) if result.result is not None else None,
            "error": None if result.error is None else f"{type(result.error).__name__}: {result.error}",
            "phase": result.phase,
            "traceback": result.traceback,
            "diagnostic": diagnostic.to_dict() if diagnostic is not None else None,
            "shapes": result.shapes or {},
        }

    def _text_payload(self, result: PyPlyneExecutionResult) -> str:
        chunks = []
        if result.stdout:
            chunks.append(result.stdout)
        if result.stderr:
            chunks.append(result.stderr)
        if result.result is not None:
            chunks.append(self._format_value(result.result) + "\n")
        if result.error is not None:
            diagnostic = build_diagnostic(result)
            chunks.append((diagnostic.format() if diagnostic else result.traceback) + "\n")
        if not chunks:
            chunks.append("ok\n")
        return "".join(chunks)

    def _format_value(self, value: Any) -> str:
        return pprint.pformat(value, width=100)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_session_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    session: Optional[PyPlyneSession] = None,
) -> PyPlyneHTTPServer:
    return PyPlyneHTTPServer((host, port), session=session)
