import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import polars as pl
import pytest

from pyplyne import run as run_pyplyne
from pyplyne import run_file as run_pyplyne_file
from pyplyne.cli import main
from pyplyne.client import run_endpoint, send_source
from pyplyne.repl import _run_source
from pyplyne.session import PyPlyneSession, create_session_server


def test_session_persists_values_and_shape_annotations_between_runs():
    session = PyPlyneSession()

    session.run("numbers = seq [1, 2, 3]\n")
    session.run("doubled = numbers |> map(_ * 2)\n")

    assert session.env["doubled"] == [2, 4, 6]
    assert session.symbol_kinds["numbers"] == "seq"
    assert session.symbol_kinds["doubled"] == "seq"


def test_session_persists_df_shape_and_polars_values_between_runs():
    session = PyPlyneSession()

    session.run(
        """
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
]
"""
    )
    session.run(
        "large_sales = sales |> where(amount > 100) |> select(region, amount)\n"
    )

    assert isinstance(session.env["sales"], pl.DataFrame)
    assert session.env["large_sales"].to_dicts() == [{"region": "north", "amount": 120}]


def test_session_getters_return_live_python_objects():
    session = PyPlyneSession()

    session.run(
        """
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
]
summary = sales
  |> where(amount > 100)
  |> select(region, amount)

records = seq [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
]
"""
    )

    summary = session.get_df("summary")
    records = session.get_seq("records")

    assert isinstance(summary, pl.DataFrame)
    assert summary.to_dicts() == [{"region": "north", "amount": 120}]
    assert records == [
        {"region": "north", "amount": 120},
        {"region": "south", "amount": 80},
    ]
    assert session.get("summary") is summary
    assert session.get("missing", default=None) is None


def test_session_getters_validate_missing_names_and_shapes():
    session = PyPlyneSession()
    session.run("numbers = seq [1, 2, 3]\nanswer = 42\n")

    with pytest.raises(KeyError, match="no value named 'missing'"):
        session.get("missing")
    with pytest.raises(TypeError, match="'numbers' is not a Polars DataFrame"):
        session.get_df("numbers")
    with pytest.raises(TypeError, match="'answer' is not a sequence"):
        session.get_seq("answer")


def test_session_load_file_values_can_be_retrieved_from_python(tmp_path):
    script = tmp_path / "pipeline.pyplyne"
    script.write_text(
        """
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
]
summary = sales
  |> where(amount > 100)
  |> select(region, amount)
""",
        encoding="utf-8",
    )

    session = PyPlyneSession()
    result = session.load_file(str(script))

    assert result.ok
    assert result.result is None
    assert session.get_df("summary").to_dicts() == [{"region": "north", "amount": 120}]


def test_session_load_file_returns_final_expression_result(tmp_path):
    script = tmp_path / "pipeline.pyplyne"
    script.write_text(
        """
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""",
        encoding="utf-8",
    )
    sales = pl.DataFrame(
        [
            {"region": "north", "amount": 120},
            {"region": "south", "amount": 80},
        ]
    )

    session = PyPlyneSession({"sales": sales})
    result = session.load_file(str(script))

    assert result.ok
    assert isinstance(result.result, pl.DataFrame)
    assert result.result.to_dicts() == [{"region": "north", "amount": 120}]
    assert session.get_df("summary") is result.result


def test_session_run_returns_inline_dataframe_final_expression():
    sales = pl.DataFrame(
        [
            {"region": "north", "amount": 120},
            {"region": "south", "amount": 80},
        ]
    )

    result = PyPlyneSession({"sales": sales}).run(
        """
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
"""
    )

    assert result.ok
    assert isinstance(result.result, pl.DataFrame)
    assert result.result.to_dicts() == [{"region": "north", "amount": 120}]


def test_one_shot_run_returns_inline_dataframe_final_expression():
    sales = pl.DataFrame(
        [
            {"region": "north", "amount": 120},
            {"region": "south", "amount": 80},
        ]
    )

    result = run_pyplyne(
        """
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""",
        context={"sales": sales},
    )

    assert result.ok
    assert isinstance(result.result, pl.DataFrame)
    assert result.result.to_dicts() == [{"region": "north", "amount": 120}]


def test_one_shot_run_does_not_persist_state_between_calls():
    first = run_pyplyne("numbers = seq [1, 2, 3]\n")
    second = run_pyplyne("numbers |> map(_ * 10)\n", raise_on_error=False)

    assert first.ok
    assert not second.ok
    assert second.phase == "compile"
    assert "map requires a known seq pipeline" in str(second.error)


def test_one_shot_run_file_returns_final_expression_result(tmp_path):
    script = tmp_path / "pipeline.pyplyne"
    script.write_text(
        """
summary = df sales
  |> where(amount > 100)
  |> select(region, amount)

summary
""",
        encoding="utf-8",
    )
    sales = pl.DataFrame(
        [
            {"region": "north", "amount": 120},
            {"region": "south", "amount": 80},
        ]
    )

    result = run_pyplyne_file(script, context={"sales": sales})

    assert result.ok
    assert isinstance(result.result, pl.DataFrame)
    assert result.result.to_dicts() == [{"region": "north", "amount": 120}]
    assert result.filename == str(script)


def test_session_expression_result_is_stored_as_underscore():
    session = PyPlyneSession()

    session.run("numbers = seq [1, 2, 3]\n")
    result = session.run("numbers |> map(_ * 10)\n")

    assert result.result == [10, 20, 30]
    assert session.env["_"] == [10, 20, 30]
    assert session.symbol_kinds["_"] == "seq"


def test_session_scalar_expression_result_clears_underscore_shape():
    session = PyPlyneSession()

    session.run("numbers = seq [1, 2, 3]\n")
    session.run("numbers |> map(_ * 10)\n")
    result = session.run("42\n")

    assert result.result == 42
    assert session.env["_"] == 42
    assert "_" not in session.symbol_kinds


def test_session_rolls_back_new_shapes_when_snippet_fails():
    session = PyPlyneSession()

    session.run("numbers = seq [1, 2, 3]\n")
    with pytest.raises(SyntaxError, match="where is a df verb"):
        session.run("broken = numbers |> where(amount > 1)\n")

    assert "broken" not in session.symbol_kinds
    assert session.symbol_kinds["numbers"] == "seq"


def test_session_run_can_return_parse_errors_without_raising():
    session = PyPlyneSession()

    result = session.run("numbers = seq [1, 2, 3\n", raise_on_error=False)

    assert not result.ok
    assert result.phase == "parse"
    assert "syntax error" in str(result.error)
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.shapes == {}
    assert "PyPlyneParseError" in result.traceback


def test_session_run_can_return_compile_errors_without_mutating_shapes():
    session = PyPlyneSession()
    session.run("numbers = seq [1, 2, 3]\n")

    result = session.run(
        "broken = numbers |> where(amount > 1)\n", raise_on_error=False
    )

    assert not result.ok
    assert result.phase == "compile"
    assert isinstance(result.error, SyntaxError)
    assert "where is a df verb" in str(result.error)
    assert result.shapes == {"numbers": "seq"}
    assert "broken" not in session.env
    assert "broken" not in session.symbol_kinds


def test_session_run_can_return_runtime_errors_and_keep_prior_statements():
    session = PyPlyneSession()

    result = session.run(
        "numbers = seq [1, 2, 3]\nnumbers |> map()\n", raise_on_error=False
    )

    assert not result.ok
    assert result.phase == "runtime"
    assert result.error is not None
    assert str(result.error) == "map() missing 1 required positional argument: 'func'"
    assert session.env["numbers"] == [1, 2, 3]
    assert result.shapes == {"numbers": "seq"}
    assert "__pyplyne_last_result__" not in session.env


def test_session_runs_are_serialized_for_threaded_servers():
    session = PyPlyneSession()

    thread = threading.Thread(
        target=lambda: session.run(
            """
import time
time.sleep(0.1)
numbers = seq [1, 2, 3]
"""
        )
    )
    thread.start()
    time.sleep(0.02)

    result = session.run("numbers |> map(_ + 1)\n", raise_on_error=False)
    thread.join(timeout=2)

    assert result.ok
    assert result.result == [2, 3, 4]


def test_http_session_runs_raw_plyne_and_persists_state_between_requests():
    session = PyPlyneSession()
    server = create_session_server("127.0.0.1", 0, session=session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/run"

    try:
        first = _post(url, b"numbers = seq [1, 2, 3]\n")
        second = _post(
            url + "?format=json", b"numbers |> map(_ + 1)\n", accept="application/json"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert first == "ok\n"
    payload = json.loads(second)
    assert payload["ok"] is True
    assert payload["result"] == "[2, 3, 4]"
    assert payload["shapes"]["numbers"] == "seq"
    assert payload["shapes"]["_"] == "seq"


def test_http_session_exposes_shapes_without_mutating_last_result():
    session = PyPlyneSession()
    server = create_session_server("127.0.0.1", 0, session=session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}"

    try:
        _post(f"{url}/run", b"numbers = seq [1, 2, 3]\n")
        _post(f"{url}/run", b"numbers |> map(_ * 10)\n")
        shapes = json.loads(_get(f"{url}/shapes"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert shapes == {"numbers": "seq", "_": "seq"}
    assert session.env["_"] == [10, 20, 30]


def test_http_session_returns_traceback_for_errors():
    server = create_session_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/run"

    try:
        with pytest.raises(HTTPError) as excinfo:
            _post(url, b'rows = seq [{"amount": 1}]\nbad = rows |> where(amount > 0)\n')
        body = excinfo.value.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert excinfo.value.status == 500
    assert body.startswith("compile error: SyntaxError: where is a df verb")
    assert "where is a df verb" in body
    assert "bad = rows |> where(amount > 0)" in body
    assert "hint: Use to_table() before df verbs" in body
    assert "Traceback" not in body


def test_http_session_json_classifies_parse_errors():
    payload = _post_json_error("numbers = seq [1, 2, 3\n")

    assert payload["ok"] is False
    assert payload["phase"] == "parse"
    assert payload["error"].startswith("PyPlyneParseError: <pyplyne-session:")
    assert ":-1:-1:" not in payload["error"]
    assert "syntax error" in payload["error"]
    assert "unexpected end of input" in payload["error"]
    assert "lark.exceptions" not in payload["error"]
    assert payload["diagnostic"]["phase"] == "parse"
    assert payload["diagnostic"]["error_type"] == "SyntaxError"
    assert payload["diagnostic"]["line"] == 1
    assert payload["diagnostic"]["source"] == "numbers = seq [1, 2, 3"
    assert payload["diagnostic"]["display"].startswith("parse error: syntax error")
    assert payload["shapes"] == {}


def test_http_session_json_classifies_compile_shape_errors_and_rolls_back():
    session = PyPlyneSession()
    session.run("existing = seq [1, 2, 3]\n")
    payload = _post_json_error(
        'rows = seq [{"amount": 1}]\nbad = rows |> where(amount > 0)\n',
        session=session,
    )

    assert payload["ok"] is False
    assert payload["phase"] == "compile"
    assert payload["error"].startswith("SyntaxError: <pyplyne-session:")
    assert "where is a df verb, but the current pipeline is seq" in payload["error"]
    assert payload["diagnostic"]["phase"] == "compile"
    assert payload["diagnostic"]["line"] == 2
    assert payload["diagnostic"]["source"] == "bad = rows |> where(amount > 0)"
    assert payload["diagnostic"]["hint"].startswith("Use to_table() before df verbs")
    assert payload["shapes"] == {"existing": "seq"}
    assert "rows" not in session.env
    assert "bad" not in session.env


def test_http_session_json_classifies_runtime_call_errors_and_keeps_prior_state():
    session = PyPlyneSession()
    payload = _post_json_error(
        "numbers = seq [1, 2, 3]\nnumbers |> map()\n", session=session
    )

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert (
        payload["error"]
        == "TypeError: map() missing 1 required positional argument: 'func'"
    )
    assert payload["shapes"] == {"numbers": "seq"}
    assert session.env["numbers"] == [1, 2, 3]
    assert "__pyplyne_last_result__" not in session.env


def test_http_session_json_classifies_runtime_file_errors(tmp_path):
    missing_path = tmp_path / "missing.csv"
    payload = _post_json_error(f'missing = df read_csv("{missing_path.as_posix()}")\n')

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert payload["error"].startswith("FileNotFoundError: ")
    assert missing_path.name in payload["error"]
    assert payload["shapes"] == {}


def test_http_session_json_classifies_bad_seq_annotation_runtime_errors():
    session = PyPlyneSession()
    payload = _post_json_error("nonsense = seq 42\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert (
        payload["error"] == "TypeError: seq annotation expects iterable data, got int"
    )
    assert payload["diagnostic"]["phase"] == "runtime"
    assert payload["diagnostic"]["line"] == 1
    assert payload["diagnostic"]["source"] == "nonsense = seq 42"
    assert payload["diagnostic"]["hint"].startswith("Use seq with iterable values")
    assert payload["shapes"] == {}
    assert "nonsense" not in session.env


def test_http_session_json_classifies_bad_df_annotation_runtime_errors():
    session = PyPlyneSession()
    payload = _post_json_error("nonsense = df 42\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert (
        payload["error"]
        == "TypeError: df annotation expects table-shaped data, got int"
    )
    assert payload["shapes"] == {}
    assert "nonsense" not in session.env


def test_repl_prints_concise_errors_without_internal_traceback(capsys):
    session = PyPlyneSession()

    _run_source(session, "nonsense = seq 42\n")
    output = capsys.readouterr()

    assert output.out.startswith(
        "runtime error: TypeError: seq annotation expects iterable data, got int\n"
    )
    assert " --> <pyplyne-session:1>:1:" in output.out
    assert "1 | nonsense = seq 42" in output.out
    assert "hint: Use seq with iterable values" in output.out
    assert output.err == ""
    assert "Traceback" not in output.out
    assert "session.py" not in output.out


def test_http_session_json_reports_legacy_shape_declarations_as_parse_errors():
    payload = _post_json_error("DF sales = []\n")

    assert payload["ok"] is False
    assert payload["phase"] == "parse"
    assert payload["error"].startswith("PyPlyneParseError: <pyplyne-session:")
    assert "shape annotations go on the right-hand side" in payload["error"]
    assert "sales = df ..." in payload["error"]


def test_http_session_json_classifies_placeholder_compile_errors():
    session = PyPlyneSession()
    session.run("numbers = seq [1, 2, 3]\n")
    payload = _post_json_error("numbers |> map(_ + _1)\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "compile"
    assert payload["error"].startswith("SyntaxError: <pyplyne-session:")
    assert "cannot mix _ with numbered placeholders" in payload["error"]
    assert payload["shapes"] == {"numbers": "seq"}


def test_http_session_json_classifies_numbered_placeholder_gap_errors():
    session = PyPlyneSession()
    session.run("numbers = seq [1, 2, 3]\n")
    payload = _post_json_error("numbers |> map(_2)\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "compile"
    assert payload["error"].startswith("SyntaxError: <pyplyne-session:")
    assert (
        "numbered placeholders must start at _1 and be consecutive" in payload["error"]
    )
    assert payload["shapes"] == {"numbers": "seq"}


def test_http_session_json_classifies_unknown_function_runtime_errors():
    session = PyPlyneSession()
    session.run("numbers = seq [1, 2, 3]\n")
    payload = _post_json_error("numbers |> nosuchverb()\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert payload["error"] == "NameError: name 'nosuchverb' is not defined"
    assert payload["shapes"] == {"numbers": "seq"}


def test_http_session_json_classifies_missing_column_runtime_errors():
    session = PyPlyneSession()
    session.run('sales = df [{"amount": 120}]\n')
    payload = _post_json_error("sales |> where(missing > 0)\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert payload["error"].startswith("ColumnNotFoundError: ")
    assert 'unable to find column "missing"' in payload["error"]
    assert '"amount"' in payload["error"]
    assert payload["shapes"] == {"sales": "df"}


def test_http_session_json_classifies_unfinished_group_by_runtime_errors():
    session = PyPlyneSession()
    session.run('sales = df [{"region": "north", "amount": 120}]\n')
    payload = _post_json_error("grouped = sales |> group_by(region)\n", session=session)

    assert payload["ok"] is False
    assert payload["phase"] == "runtime"
    assert payload["error"].startswith("TypeError: ")
    assert "group_by(...) must be followed by summarize" in payload["error"]
    assert payload["shapes"] == {"sales": "df"}


def test_client_builds_default_and_overridden_run_urls(monkeypatch):
    assert run_endpoint() == "http://127.0.0.1:8765/run"
    assert run_endpoint(host="0.0.0.0", port=9000) == "http://0.0.0.0:9000/run"
    assert (
        run_endpoint(url="127.0.0.1:9999", json_output=True)
        == "http://127.0.0.1:9999/run?format=json"
    )

    monkeypatch.setenv("PYPLYNE_URL", "http://example.test:1234")
    assert run_endpoint() == "http://example.test:1234/run"


def test_client_send_source_uses_port_override_and_persists_state():
    server = create_session_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        first = send_source("numbers = seq [1, 2, 3]\n", host=host, port=port)
        second = send_source(
            "numbers |> map(_ * 10)\n", host=host, port=port, json_output=True
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert first.ok
    assert first.body == "ok\n"
    payload = json.loads(second.body)
    assert second.ok
    assert payload["result"] == "[10, 20, 30]"


def test_send_cli_sends_expression_to_port_override(capsys):
    server = create_session_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        assert (
            main(
                [
                    "send",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--expr",
                    "numbers = seq [1, 2]",
                ]
            )
            == 0
        )
        first = capsys.readouterr()
        assert (
            main(
                [
                    "send",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--expr",
                    "numbers |> map(_ + 1)",
                ]
            )
            == 0
        )
        second = capsys.readouterr()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert first.out == "ok\n"
    assert second.out == "[2, 3]\n"
    assert first.err == ""
    assert second.err == ""


def test_send_cli_source_name_sets_virtual_diagnostic_filename(capsys):
    server = create_session_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        assert (
            main(
                [
                    "send",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--json",
                    "--source-name",
                    "agent-step-01.pyplyne",
                    "--expr",
                    "numbers = seq [1, 2]",
                ]
            )
            == 0
        )
        output = capsys.readouterr()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    payload = json.loads(output.out)
    assert payload["filename"] == "agent-step-01.pyplyne"
    assert output.err == ""


def test_send_cli_returns_nonzero_and_stderr_for_server_errors(capsys):
    server = create_session_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        exit_code = main(
            [
                "send",
                "--host",
                host,
                "--port",
                str(port),
                "--expr",
                'rows = seq [{"amount": 1}]\nbad = rows |> where(amount > 0)',
            ]
        )
        output = capsys.readouterr()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert exit_code == 1
    assert output.out == ""
    assert "where is a df verb" in output.err


def _post(url: str, body: bytes, accept: str = "text/plain") -> str:
    request = Request(url, data=body, method="POST", headers={"Accept": accept})
    with urlopen(request, timeout=5) as response:
        return response.read().decode("utf-8")


def _get(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _post_json_error(
    source: str, session: PyPlyneSession | None = None
) -> dict[str, object]:
    server = create_session_server("127.0.0.1", 0, session=session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/run?format=json"

    try:
        with pytest.raises(HTTPError) as excinfo:
            _post(url, source.encode("utf-8"), accept="application/json")
        return json.loads(excinfo.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
