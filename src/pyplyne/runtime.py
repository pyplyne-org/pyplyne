from __future__ import annotations

import builtins
import csv
import functools
import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import polars as pl

_missing = object()


class _MissingField:
    def __init__(self, name: str) -> None:
        self.name = name

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return False

    def __ne__(self, other: object) -> bool:
        return True

    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return False

    def __repr__(self) -> str:
        return f"<missing field {self.name!r}>"


def map(data: Iterable[Any], func: Callable[[Any], Any]) -> list[Any]:
    return [func(item) for item in data]


def filter(data: Iterable[Any], predicate: Callable[[Any], bool]) -> list[Any]:
    return [item for item in data if predicate(item)]


def reduce(
    data: Iterable[Any], func: Callable[[Any, Any], Any], initial: Any = _missing
) -> Any:
    iterator = iter(data)
    if initial is _missing:
        return functools.reduce(func, iterator)
    return functools.reduce(func, iterator, initial)


def set_fields(data: Iterable[Any], **assignments: Any) -> list[dict[str, Any]]:
    rows = []
    for row in data:
        next_row = _row_dict(row, "set_fields")
        for name, value in assignments.items():
            next_row[name] = value(row) if callable(value) else value
        rows.append(next_row)
    return rows


def drop_fields(data: Iterable[Any], *fields: str) -> list[dict[str, Any]]:
    field_names = set(fields)
    rows = []
    for row in data:
        next_row = _row_dict(row, "drop_fields")
        for field in field_names:
            next_row.pop(field, None)
        rows.append(next_row)
    return rows


def keep_fields(data: Iterable[Any], *fields: str) -> list[dict[str, Any]]:
    rows = []
    for row in data:
        source = _row_dict(row, "keep_fields")
        rows.append({field: source[field] for field in fields if field in source})
    return rows


def collect(data: Any) -> Any:
    if hasattr(data, "collect") and callable(data.collect):
        return data.collect()
    return data


def to_rows(data: Any) -> list[Any]:
    if isinstance(data, pl.LazyFrame):
        return data.collect().to_dicts()
    if isinstance(data, pl.DataFrame):
        return data.to_dicts()
    if isinstance(data, Mapping):
        return [dict(data)]
    return [dict(row) if isinstance(row, Mapping) else row for row in data]


def to_table(data: Any) -> pl.DataFrame:
    if isinstance(data, pl.LazyFrame):
        return data.collect()
    if isinstance(data, pl.DataFrame):
        return data
    if isinstance(data, Mapping):
        return pl.DataFrame([data])
    return pl.DataFrame(data)


def _auto(data: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        return data.collect()
    if _is_polars_group_by(data):
        raise TypeError(
            "group_by(...) must be followed by summarize(...) before the pipeline can run"
        )
    return data


def _as_df(data: Any) -> pl.DataFrame:
    if isinstance(data, pl.LazyFrame):
        return data.collect()
    if isinstance(data, pl.DataFrame):
        return data
    if _is_polars_group_by(data):
        raise TypeError(
            "group_by(...) must be followed by summarize(...) before assigning to a df"
        )
    if isinstance(data, Mapping):
        return pl.DataFrame([data])
    try:
        return pl.DataFrame(data)
    except TypeError:
        raise TypeError(
            f"df annotation expects table-shaped data, got {_type_name(data)}"
        ) from None


def _as_seq(data: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        return data.collect().to_dicts()
    if isinstance(data, pl.DataFrame):
        return data.to_dicts()
    if isinstance(data, Mapping):
        raise TypeError(
            "seq annotation expects iterable data, got mapping; wrap it in [...] for a row sequence"
        )
    if isinstance(data, (str, bytes, bytearray)):
        raise TypeError(f"seq annotation expects iterable data, got {_type_name(data)}")
    if not isinstance(data, Iterable):
        raise TypeError(f"seq annotation expects iterable data, got {_type_name(data)}")
    return data


def read_csv(path: str | Path, **kwargs: Any) -> Any:
    return pl.scan_csv(path, **kwargs)


def read_json(path: str | Path, **kwargs: Any) -> pl.DataFrame:
    return pl.read_json(path, **kwargs)


def read_parquet(path: str | Path, **kwargs: Any) -> pl.DataFrame:
    return pl.read_parquet(path, **kwargs)


def read_excel(path: str | Path, **kwargs: Any) -> Any:
    return pl.read_excel(path, **kwargs)


def write_csv(data: Any, path: str | Path, **kwargs: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        data.sink_csv(path, **kwargs)
        return data

    if isinstance(data, pl.DataFrame):
        data.write_csv(path, **kwargs)
        return data

    rows = list(data)
    if not rows:
        Path(path).write_text("", encoding=kwargs.pop("encoding", "utf-8"))
        return data

    with Path(path).open(
        "w", newline="", encoding=kwargs.pop("encoding", "utf-8")
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), **kwargs)
        writer.writeheader()
        writer.writerows(rows)
    return data


def write_json(data: Any, path: str | Path, **kwargs: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        data = data.collect()

    if isinstance(data, pl.DataFrame):
        data.write_json(path, **kwargs)
        return data

    Path(path).write_text(json.dumps(data, **kwargs), encoding="utf-8")
    return data


def write_parquet(data: Any, path: str | Path, **kwargs: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        data.sink_parquet(path, **kwargs)
        return data

    if isinstance(data, pl.DataFrame):
        data.write_parquet(path, **kwargs)
        return data

    pl.DataFrame(data).write_parquet(path, **kwargs)
    return data


def write_excel(data: Any, path: str | Path, **kwargs: Any) -> Any:
    if isinstance(data, pl.LazyFrame):
        data = data.collect()

    if isinstance(data, pl.DataFrame):
        data.write_excel(path, **kwargs)
        return data

    pl.DataFrame(data).write_excel(path, **kwargs)
    return data


def select(data: Any, *columns: str) -> Any:
    if _has_polars_expr(columns) or _is_polars_table(data):
        return _to_lazy(data).select(*columns)
    if isinstance(data, list):
        return [{column: row[column] for column in columns} for row in data]
    if isinstance(data, Mapping):
        return {column: data[column] for column in columns}
    raise TypeError("select() expects a Polars table, row dict, or list of row dicts")


def where(data: Any, predicate: Callable[[Any], bool] | str) -> Any:
    if isinstance(predicate, pl.Expr) or _is_polars_table(data):
        return _to_lazy(data).filter(predicate)
    if callable(predicate):
        return [item for item in data if predicate(item)]
    raise TypeError("where() expects a Polars expression or callable predicate")


def mutate(data: Any, **assignments: Any) -> Any:
    if _has_polars_expr(assignments.values()) or _is_polars_table(data):
        return _to_lazy(data).with_columns(
            **{name: _into_polars_expr(value) for name, value in assignments.items()}
        )

    if isinstance(data, list):
        rows = []
        for row in data:
            next_row = dict(row)
            for name, value in assignments.items():
                next_row[name] = value(row) if callable(value) else value
            rows.append(next_row)
        return rows

    raise TypeError("mutate() expects a Polars table or list of row dicts")


def group_by(data: Any, *columns: str) -> Any:
    return _to_lazy(data).group_by(*columns)


def summarize(data: Any, **aggregations: Any) -> Any:
    if hasattr(data, "agg"):
        return data.agg(**aggregations)
    return _to_lazy(data).select(
        *[_into_polars_expr(value).alias(name) for name, value in aggregations.items()]
    )


def arrange(data: Any, *by: Any, descending: bool = False) -> Any:
    return _to_lazy(data).sort(*by, descending=descending)


def _col(name: str) -> pl.Expr:
    return pl.col(name)


def _sum(value: Any) -> Any:
    return value.sum() if isinstance(value, pl.Expr) else builtins.sum(value)


def _mean(value: Any) -> Any:
    if isinstance(value, pl.Expr):
        return value.mean()
    values = list(value)
    return builtins.sum(values) / len(values)


def _min(value: Any) -> Any:
    return value.min() if isinstance(value, pl.Expr) else builtins.min(value)


def _max(value: Any) -> Any:
    return value.max() if isinstance(value, pl.Expr) else builtins.max(value)


def _count(value: Any | None = None) -> pl.Expr:
    if value is None:
        return pl.len()
    return value.count() if isinstance(value, pl.Expr) else pl.lit(len(value))


def _is_polars_table(data: Any) -> bool:
    return isinstance(data, (pl.DataFrame, pl.LazyFrame))


def _is_polars_group_by(data: Any) -> bool:
    return data.__class__.__name__.endswith("GroupBy") and hasattr(data, "agg")


def _type_name(data: Any) -> str:
    return type(data).__name__


def _row_dict(row: Any, verb: str) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    raise TypeError(f"{verb}() expects a sequence of row dictionaries")


def _field(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(name, _MissingField(name))
    return getattr(row, name, _MissingField(name))


def _to_lazy(data: Any) -> pl.LazyFrame:
    if isinstance(data, pl.LazyFrame):
        return data
    if isinstance(data, pl.DataFrame):
        return data.lazy()
    if isinstance(data, list) and all(isinstance(row, Mapping) for row in data):
        return pl.DataFrame(data).lazy()
    raise TypeError("expected a Polars table or list of row dicts")


def _has_polars_expr(values: Iterable[Any]) -> bool:
    return any(isinstance(value, pl.Expr) for value in values)


def _into_polars_expr(value: Any) -> pl.Expr:
    return value if isinstance(value, pl.Expr) else pl.lit(value)


def runtime_globals() -> dict[str, Any]:
    env = {
        "__builtins__": builtins.__dict__,
        "map": map,
        "filter": filter,
        "reduce": reduce,
        "set_fields": set_fields,
        "drop_fields": drop_fields,
        "keep_fields": keep_fields,
        "collect": collect,
        "to_rows": to_rows,
        "to_table": to_table,
        "read_csv": read_csv,
        "read_json": read_json,
        "read_parquet": read_parquet,
        "read_excel": read_excel,
        "write_csv": write_csv,
        "write_json": write_json,
        "write_parquet": write_parquet,
        "write_excel": write_excel,
        "select": select,
        "where": where,
        "mutate": mutate,
        "group_by": group_by,
        "summarize": summarize,
        "arrange": arrange,
        "_col": _col,
        "_sum": _sum,
        "_mean": _mean,
        "_min": _min,
        "_max": _max,
        "_count": _count,
        "_field": _field,
        "_auto": _auto,
        "_as_df": _as_df,
        "_as_seq": _as_seq,
    }
    return env
