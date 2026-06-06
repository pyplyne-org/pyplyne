from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Optional, Union

from lark import Lark, Tree
from lark.exceptions import UnexpectedEOF, UnexpectedInput


GRAMMAR_PATH = Path(__file__).with_name("grammar.lark")
LEGACY_SHAPE_DECL_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<kind>df|seq|DF|Df|SEQ|Seq)\s+(?P<name>\w+)\s*=",
    re.MULTILINE,
)


class PyPlyneParseError(SyntaxError):
    """Syntax error raised while parsing PyPlyne source."""

    phase = "parse"


@lru_cache(maxsize=1)
def get_parser() -> Lark:
    """Return the cached Lark parser for PyPlyne source."""

    return Lark(
        GRAMMAR_PATH.read_text(encoding="utf-8"),
        parser="earley",
        ambiguity="resolve",
        propagate_positions=True,
        maybe_placeholders=False,
    )


def parse_source(source: str, filename: str = "<pyplyne>") -> Tree:
    """Parse PyPlyne source text into a Lark parse tree.

    Args:
        source: PyPlyne source code to parse.
        filename: Virtual filename used in diagnostics.

    Returns:
        Tree: Lark parse tree ready to pass to `compile_ast`.

    Raises:
        PyPlyneParseError: Source text is not valid PyPlyne syntax.
    """

    _reject_legacy_shape_declarations(source, filename)
    try:
        return get_parser().parse(source)
    except UnexpectedInput as exc:
        raise PyPlyneParseError(_format_parse_error(source, filename, exc)) from None


def parse_file(path: Union[str, Path]) -> Tree:
    """Parse a `.pyplyne` file from disk."""

    file_path = Path(path)
    return parse_source(file_path.read_text(encoding="utf-8"), filename=str(file_path))


def _reject_legacy_shape_declarations(source: str, filename: str) -> None:
    match = LEGACY_SHAPE_DECL_PATTERN.search(source)
    if not match:
        return

    line = source.count("\n", 0, match.start("kind")) + 1
    last_newline = source.rfind("\n", 0, match.start("kind"))
    column = match.start("kind") + 1 if last_newline == -1 else match.start("kind") - last_newline
    found = match.group("kind")
    expected = found.lower()
    name = match.group("name")
    raise PyPlyneParseError(
        f"{filename}:{line}:{column}: syntax error: shape annotations go on the right-hand side; "
        f"use `{name} = {expected} ...`"
    )


def _format_parse_error(source: str, filename: str, exc: UnexpectedInput) -> str:
    line, column = _error_location(source, exc)
    message = f"{filename}:{line}:{column}: syntax error"

    if isinstance(exc, UnexpectedEOF):
        message += ": unexpected end of input"
    else:
        token = getattr(exc, "token", None)
        char = getattr(exc, "char", None)
        if token is not None:
            message += f": unexpected {token!s}"
        elif char is not None:
            message += f": unexpected {char!r}"

    expected = _expected_tokens(getattr(exc, "expected", None))
    if expected:
        message += f"; expected one of: {', '.join(expected)}"

    context = _context(source, exc)
    if context:
        message += f"\n{context}"
    return message


def _error_location(source: str, exc: UnexpectedInput) -> tuple[int, int]:
    line = getattr(exc, "line", None)
    column = getattr(exc, "column", None)
    if line is not None and column is not None and int(line) > 0 and int(column) > 0:
        return int(line), int(column)

    lines = source.splitlines()
    if not lines:
        return 1, 1
    return len(lines), len(lines[-1]) + 1


def _expected_tokens(expected: Optional[set[str]]) -> list[str]:
    if not expected:
        return []
    names = {_friendly_token_name(name) for name in expected}
    return sorted(name for name in names if name)


def _friendly_token_name(name: str) -> str:
    return {
        "_NL": "newline",
        "RSQB": "]",
        "LSQB": "[",
        "RPAR": ")",
        "LPAR": "(",
        "RBRACE": "}",
        "LBRACE": "{",
        "COMMA": ",",
        "DOT": ".",
        "NAME": "name",
        "STRING": "string",
        "SIGNED_NUMBER": "number",
        "__ANON_0": "|>",
    }.get(name, name)


def _context(source: str, exc: UnexpectedInput) -> str:
    try:
        return exc.get_context(source, span=60).rstrip()
    except Exception:
        return ""
