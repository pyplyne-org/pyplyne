from __future__ import annotations

from pyplyne.diagnostics import build_diagnostic
from pyplyne.session import PyPlyneSession

PROMPT = "pyplyne> "
MORE_PROMPT = "...   "


def run_repl(session: PyPlyneSession | None = None) -> int:
    session = session or PyPlyneSession()
    buffer: list[str] = []
    print(
        "PyPlyne interactive session. End assignment blocks with a blank line. Use :paste for multi-line paste."
    )

    while True:
        try:
            line = input(MORE_PROMPT if buffer else PROMPT)
        except EOFError:
            print()
            return 0

        command = line.strip()
        if not buffer and command in {":quit", ":q", "exit", "quit"}:
            return 0
        if not buffer and command == ":shapes":
            print(session.symbol_kinds)
            continue
        if not buffer and command == ":vars":
            names = sorted(name for name in session.env if not name.startswith("__"))
            print(names)
            continue
        if not buffer and command == ":help":
            print(":help, :paste, :vars, :shapes, :quit")
            continue
        if not buffer and command == ":paste":
            source = _read_paste()
            if source.strip():
                _run_source(session, source)
            continue

        if not line and buffer:
            source = "\n".join(buffer) + "\n"
            buffer.clear()
            _run_source(session, source)
            continue
        if not line:
            continue

        buffer.append(line)
        if _looks_complete(buffer):
            source = "\n".join(buffer) + "\n"
            buffer.clear()
            _run_source(session, source)


def _run_source(session: PyPlyneSession, source: str) -> None:
    result = session.run(source, raise_on_error=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.result is not None:
        print(repr(result.result))
    if result.error is not None:
        print(_format_error(result))


def _format_error(result) -> str:
    diagnostic = build_diagnostic(result)
    if diagnostic is not None:
        return diagnostic.format()
    phase = f"{result.phase} " if result.phase else ""
    error = result.error
    return f"{phase}error: {type(error).__name__}: {error}"


def _read_paste() -> str:
    print("Paste PyPlyne code. End with a single '.' on its own line.")
    lines = []
    while True:
        try:
            line = input(MORE_PROMPT)
        except EOFError:
            break
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines) + "\n"


def _looks_complete(lines: list[str]) -> bool:
    last = lines[-1].rstrip()
    if last.endswith("|>"):
        return False
    if _bracket_depth("\n".join(lines)) > 0:
        return False
    if len(lines) == 1 and "=" in last and "|>" not in last:
        return False
    if len(lines) > 1 and (
        lines[-1].startswith((" ", "\t")) or lines[-2].rstrip().endswith("|>")
    ):
        return False
    return True


def _bracket_depth(source: str) -> int:
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = {")", "]", "}"}
    stack = []
    in_string: str | None = None
    escaped = False
    for char in source:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {"'", '"'}:
            in_string = char
        elif char in pairs:
            stack.append(pairs[char])
        elif char in closers:
            if stack and stack[-1] == char:
                stack.pop()
    return len(stack)
