---
title: Generated Python API Reference
description: Public Python API signatures generated from the current PyPlyne package.
---

# Generated Python API Reference

This page is generated from the public Python API signatures and docstrings.
Update the package source first, then regenerate with `npm run docs:api` from
`site/`.

## Public Surface

| API | Use it for |
| --- | --- |
| `run` | Run PyPlyne source once without managing a persistent session. |
| `run_file` | Run a `.pyplyne` file once without managing a persistent session. |
| `PyPlyneSession` | Persistent PyPlyne execution environment. |
| `PyPlyneExecutionResult` | Result object returned by `PyPlyneSession.run`. |
| `parse_source` | Parse PyPlyne source text into a Lark parse tree. |
| `compile_ast` | Compile a PyPlyne parse tree into a Python AST module. |

## `run`

```python
run(
    source: 'str',
    context: 'Optional[dict[str, Any]]' = None,
    filename: 'str' = '<pyplyne>',
    *,
    capture_output: 'bool' = True,
    raise_on_error: 'bool' = True,
    store_result: 'bool' = True,
) -> 'PyPlyneExecutionResult'
```

Run PyPlyne source once without managing a persistent session.

### Parameters

| Name | Description |
| --- | --- |
| `source` | PyPlyne source code to execute. |
| `context` | Optional Python names and values available to the source. |
| `filename` | Virtual filename used in diagnostics. |
| `capture_output` | Capture stdout/stderr into the result object. When false, output goes to the process streams and the result stream fields are empty. |
| `raise_on_error` | Raise failures instead of returning a non-ok result. |
| `store_result` | Capture the final expression result. |

### Returns

| Type | Description |
| --- | --- |
| `PyPlyneExecutionResult` | Captured output, result value, shapes, and any non-raised error from the one-shot run. |

## `run_file`

```python
run_file(
    path: 'str | Path',
    context: 'Optional[dict[str, Any]]' = None,
    *,
    capture_output: 'bool' = True,
    raise_on_error: 'bool' = True,
    store_result: 'bool' = True,
) -> 'PyPlyneExecutionResult'
```

Run a `.pyplyne` file once without managing a persistent session.

### Parameters

| Name | Description |
| --- | --- |
| `path` | Path to the `.pyplyne` source file. |
| `context` | Optional Python names and values available to the file. |
| `capture_output` | Capture stdout/stderr into the result object. When false, output goes to the process streams and the result stream fields are empty. |
| `raise_on_error` | Raise failures instead of returning a non-ok result. |
| `store_result` | Capture the final expression result. |

### Returns

| Type | Description |
| --- | --- |
| `PyPlyneExecutionResult` | Captured output, result value, shapes, and any non-raised error from the one-shot file run. |

## `PyPlyneSession`

```python
PyPlyneSession(globals_dict: 'Optional[dict[str, Any]]' = None) -> 'None'
```

Persistent PyPlyne execution environment.

A session keeps Python globals, imports, runtime helpers, known `df`/`seq`
shapes, and the most recent expression result across runs.

### Parameters

| Name | Description |
| --- | --- |
| `globals_dict` | Initial names and values to add to the session environment. |

### `PyPlyneSession.run`

```python
run(
    self,
    source: 'str',
    filename: 'Optional[str]' = None,
    *,
    capture_output: 'bool' = True,
    raise_on_error: 'bool' = True,
    store_result: 'bool' = True,
) -> 'PyPlyneExecutionResult'
```

Compile and execute PyPlyne source in this persistent session.

#### Parameters

| Name | Description |
| --- | --- |
| `source` | PyPlyne source code to execute. |
| `filename` | Optional virtual filename used in diagnostics. |
| `capture_output` | Capture stdout/stderr into the result object. When false, output goes to the process streams and the result stream fields are empty. |
| `raise_on_error` | Raise failures instead of returning a non-ok result. |
| `store_result` | Capture the final expression result and store it as `_`. Assignment-only snippets do not replace `_`. |

#### Returns

| Type | Description |
| --- | --- |
| `PyPlyneExecutionResult` | Captured output, result value, shapes, and any non-raised error. |

#### Raises

| Type | Description |
| --- | --- |
| `Exception` | Re-raises parse, compile, or runtime failures when `raise_on_error` is true. |

### `PyPlyneSession.load_file`

```python
load_file(self, path: 'str') -> 'PyPlyneExecutionResult'
```

Run a `.pyplyne` file inside this session.

`load_file` uses the default `run` behavior, including raising on
errors. Read the file and call `run(..., raise_on_error=False)` when
non-raising file execution is needed.

#### Parameters

| Name | Description |
| --- | --- |
| `path` | Path to the `.pyplyne` source file. |

#### Returns

| Type | Description |
| --- | --- |
| `PyPlyneExecutionResult` | Result from running the file contents. |

### `PyPlyneSession.get`

```python
get(self, name: 'str', default: 'Any' = MISSING) -> 'Any'
```

Return a named value from the session environment.

#### Parameters

| Name | Description |
| --- | --- |
| `name` | Name to read from the session. |
| `default` | Optional fallback returned when the name is missing. |

#### Returns

| Type | Description |
| --- | --- |
| `Any` | The live Python object stored in the session. |

#### Raises

| Type | Description |
| --- | --- |
| `KeyError` | If the name is missing and no default was supplied. |

### `PyPlyneSession.get_df`

```python
get_df(self, name: 'str') -> 'pl.DataFrame'
```

Return a named value as a Polars DataFrame.

#### Parameters

| Name | Description |
| --- | --- |
| `name` | Name to read from the session. |

#### Returns

| Type | Description |
| --- | --- |
| `polars.DataFrame` | The live DataFrame stored in the session. |

#### Raises

| Type | Description |
| --- | --- |
| `KeyError` | If the name is missing. |
| `TypeError` | If the named value is not a Polars DataFrame. |

### `PyPlyneSession.get_seq`

```python
get_seq(self, name: 'str') -> 'list[Any] | tuple[Any, ...]'
```

Return a named value as a sequence.

#### Parameters

| Name | Description |
| --- | --- |
| `name` | Name to read from the session. |

#### Returns

| Type | Description |
| --- | --- |
| `list | tuple` | The live sequence stored in the session. |

#### Raises

| Type | Description |
| --- | --- |
| `KeyError` | If the name is missing. |
| `TypeError` | If the named value is not a list or tuple. |

## `PyPlyneExecutionResult`

```python
PyPlyneExecutionResult(
    filename: 'str',
    stdout: 'str',
    stderr: 'str',
    result: 'Any' = None,
    error: 'Optional[BaseException]' = None,
    phase: 'Optional[str]' = None,
    traceback: 'str' = '',
    shapes: 'Optional[dict[str, str]]' = None,
) -> None
```

Result object returned by `PyPlyneSession.run`.

`ok` is true when execution completed without an error. When `ok` is false,
`phase`, `error`, `traceback`, and `stderr` describe what failed.

### Fields

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `filename` | `str` | `required` | Virtual filename used for diagnostics and tracebacks. |
| `stdout` | `str` | `required` | Text written to standard output while the source ran. |
| `stderr` | `str` | `required` | Text written to standard error while the source ran. |
| `result` | `Any` | `None` | Final expression value when `store_result` is true and the snippet ends with an expression. |
| `error` | `Optional[BaseException]` | `None` | Exception captured from parsing, compiling, or running the source. |
| `phase` | `Optional[str]` | `None` | Failure phase, usually `parse`, `compile`, or `runtime`. |
| `traceback` | `str` | `''` | Python traceback text for captured errors. |
| `shapes` | `Optional[dict[str, str]]` | `None` | Known `df` and `seq` variable shapes after the run. |

### Properties

| Property | Description |
| --- | --- |
| `ok` | Whether the run completed without a captured error. |

## `parse_source`

```python
parse_source(source: 'str', filename: 'str' = '<pyplyne>') -> 'Tree'
```

Parse PyPlyne source text into a Lark parse tree.

### Parameters

| Name | Description |
| --- | --- |
| `source` | PyPlyne source code to parse. |
| `filename` | Virtual filename used in diagnostics. |

### Returns

| Type | Description |
| --- | --- |
| `Tree` | Lark parse tree ready to pass to `compile_ast`. |

### Raises

| Type | Description |
| --- | --- |
| `PyPlyneParseError` | Source text is not valid PyPlyne syntax. |

## `compile_ast`

```python
compile_ast(
    tree: 'Tree',
    filename: 'str' = '<pyplyne>',
    symbol_kinds: 'Optional[dict[str, str]]' = None,
) -> 'ast.Module'
```

Compile a PyPlyne parse tree into a Python AST module.

### Parameters

| Name | Description |
| --- | --- |
| `tree` | Parse tree returned by `parse_source`. |
| `filename` | Virtual filename copied into generated AST nodes. |
| `symbol_kinds` | Optional shape registry used to validate `df` and `seq` pipelines across session runs. |

### Returns

| Type | Description |
| --- | --- |
| `ast.Module` | Python AST module that can be compiled with `compile`. |

### Raises

| Type | Description |
| --- | --- |
| `SyntaxError` | The parse tree contains an invalid PyPlyne construct. |

