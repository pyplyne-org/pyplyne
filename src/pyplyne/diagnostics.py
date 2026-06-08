from __future__ import annotations

import linecache
import re
from dataclasses import dataclass
from typing import Any

LOCATION_RE = re.compile(
    r"^(?P<filename>.+):(?P<line>\d+):(?P<column>\d+): (?P<message>.*)$"
)
TRACEBACK_FILE_RE = re.compile(
    r'^\s*File "(?P<filename>.+)", line (?P<line>\d+), in .*$'
)


@dataclass(frozen=True)
class Diagnostic:
    phase: str | None
    error_type: str
    message: str
    filename: str
    line: int | None = None
    column: int | None = None
    source: str | None = None
    caret: str | None = None
    hint: str | None = None

    def format(self) -> str:
        phase = f"{self.phase} " if self.phase else ""
        error_text = self.message
        if not self.message.startswith("syntax error"):
            error_text = f"{self.error_type}: {self.message}"

        lines = [f"{phase}error: {error_text}"]
        if self.line is not None:
            location = f"{self.filename}:{self.line}"
            if self.column is not None:
                location += f":{self.column}"
            lines.append(f" --> {location}")
        if self.source is not None:
            line_no = str(self.line) if self.line is not None else ""
            gutter = " " * len(line_no)
            lines.append(f"{gutter} |")
            lines.append(f"{line_no} | {self.source}")
            if self.caret:
                lines.append(f"{gutter} | {self.caret}")
        if self.hint:
            lines.append(f"hint: {self.hint}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "error_type": self.error_type,
            "message": self.message,
            "filename": self.filename,
            "line": self.line,
            "column": self.column,
            "source": self.source,
            "caret": self.caret,
            "hint": self.hint,
            "display": self.format(),
        }


def build_diagnostic(result: Any) -> Diagnostic | None:
    if result.error is None:
        return None

    error = result.error
    raw_message = str(error).strip()
    first_line = raw_message.splitlines()[0] if raw_message else type(error).__name__
    error_type = _public_error_type(error)
    filename = result.filename
    line: int | None = None
    column: int | None = None
    message = first_line

    location = LOCATION_RE.match(first_line)
    if location:
        filename = location.group("filename")
        line = _positive_int(location.group("line"))
        column = _positive_int(location.group("column"))
        message = location.group("message")

    traceback_location = _location_from_traceback(result.traceback, result.filename)
    if traceback_location:
        line = line or traceback_location.line
        column = column or traceback_location.column
        filename = result.filename

    source = _source_line(filename, line)
    caret = _caret(column) if column is not None else None
    if source is None and traceback_location is not None:
        source = traceback_location.source
        caret = caret or traceback_location.caret

    return Diagnostic(
        phase=result.phase,
        error_type=error_type,
        message=message,
        filename=filename,
        line=line,
        column=column,
        source=source,
        caret=caret,
        hint=_hint(message, error_type),
    )


@dataclass(frozen=True)
class _TracebackLocation:
    line: int
    column: int | None = None
    source: str | None = None
    caret: str | None = None


def _public_error_type(error: BaseException) -> str:
    if type(error).__name__ == "PyPlyneParseError":
        return "SyntaxError"
    return type(error).__name__


def _location_from_traceback(
    traceback_text: str, filename: str
) -> _TracebackLocation | None:
    lines = traceback_text.splitlines()
    for index, line in enumerate(lines):
        match = TRACEBACK_FILE_RE.match(line)
        if not match or match.group("filename") != filename:
            continue

        source = _traceback_source_line(lines, index + 1)
        caret_line = _traceback_source_line(lines, index + 2)
        column = None
        caret = None
        if caret_line and "^" in caret_line:
            column = caret_line.index("^") + 1
            caret = " " * (column - 1) + "^"
        return _TracebackLocation(
            line=int(match.group("line")),
            column=column,
            source=source,
            caret=caret,
        )
    return None


def _traceback_source_line(lines: list[str], index: int) -> str | None:
    if index >= len(lines):
        return None
    line = lines[index]
    if not line.startswith("    "):
        return None
    return line[4:]


def _source_line(filename: str, line: int | None) -> str | None:
    if line is None:
        return None
    source = linecache.getline(filename, line)
    if not source:
        return None
    return source.rstrip("\n")


def _caret(column: int) -> str:
    return " " * max(column - 1, 0) + "^"


def _positive_int(value: str) -> int | None:
    number = int(value)
    if number < 1:
        return None
    return number


def _hint(message: str, error_type: str) -> str | None:
    if "seq annotation expects iterable data" in message:
        return "Use seq with iterable values, or wrap a scalar in [...] for a one-item sequence."
    if "df annotation expects table-shaped data" in message:
        return "Use df with dictionaries, row lists, DataFrames, LazyFrames, or file/table reads."
    if "is a df verb, but the current pipeline is seq" in message:
        return "Use to_table() before df verbs, or start the source with df if it is table-shaped."
    if "is a seq verb, but the current pipeline is df" in message:
        return "Use to_rows() before seq verbs, or start the source with seq if it is sequence-shaped."
    if "requires a known seq pipeline" in message:
        return "Annotate the pipeline source with seq, for example: result = seq values |> map(...)."
    if "requires a known df pipeline" in message:
        return "Annotate the pipeline source with df, for example: result = df values |> where(...)."
    if "shape annotations go on the right-hand side" in message:
        return 'Write the annotation after =, for example: sales = df read_csv("sales.csv").'
    if "group_by(...) must be followed by summarize" in message:
        return "Add summarize(...) after group_by(...), or remove group_by(...) before materializing."
    if error_type == "ColumnNotFoundError":
        return "Check the column name, or inspect the table columns before this step."
    return None
