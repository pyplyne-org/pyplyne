import ast
from pathlib import Path

import polars as pl
import pytest

from pyplyne.parser import parse_source
from pyplyne.cli import run_file, run_source
from pyplyne.transformer import compile_ast, iter_nodes


def test_list_pipeline_runs():
    env = run_source(
        """
numbers = seq [1, 2, 3, 4, 5]
result = numbers
  |> filter(_ % 2 == 1)
  |> map(_ * 10)
""",
        filename="list_test.pyplyne",
    )

    assert env["result"] == [10, 30, 50]


def test_arrow_lambda_runs():
    env = run_source(
        """
numbers = seq [1, 2, 3]
result = numbers
  |> map(x => x * 3)
""",
        filename="arrow_test.pyplyne",
    )

    assert env["result"] == [3, 6, 9]


def test_multi_arg_arrow_lambda_runs():
    env = run_source(
        """
numbers = seq [1, 2, 3, 4]
result = numbers
  |> reduce((total, x) => total + x)
""",
        filename="multi_arrow_test.pyplyne",
    )

    assert env["result"] == 10


def test_numbered_placeholders_run():
    env = run_source(
        """
numbers = seq [1, 2, 3, 4]
result = numbers
  |> reduce(_1 + _2)
""",
        filename="numbered_placeholder_test.pyplyne",
    )

    assert env["result"] == 10


def test_numbered_placeholders_must_start_at_one_and_be_consecutive():
    with pytest.raises(SyntaxError, match="numbered placeholders must start at _1 and be consecutive"):
        run_source(
            """
numbers = seq [1, 2, 3]
result = numbers |> map(_2)
""",
            filename="numbered_placeholder_gap_test.pyplyne",
        )


def test_reduce_pipeline_result_is_stored_as_scalar():
    env = run_source(
        """
numbers = seq [1, 2, 3]
total = numbers |> reduce(_1 + _2)
""",
        filename="reduce_scalar_shape_test.pyplyne",
    )

    assert env["total"] == 6


def test_sequence_record_field_verbs_transform_row_dicts():
    env = run_source(
        """
rows = seq [
  {"region": "north", "amount": 120, "temp": "x"},
  {"region": "south", "amount": 80, "temp": "y"},
]
reviewed = rows
  |> set_fields(reviewed=True, double=amount * 2, label=region + "-" + str(amount))
  |> drop_fields(temp)
  |> keep_fields(region, amount, double, label, reviewed)
""",
        filename="sequence_record_verbs_test.pyplyne",
    )

    assert env["reviewed"] == [
        {"region": "north", "amount": 120, "double": 240, "label": "north-120", "reviewed": True},
        {"region": "south", "amount": 80, "double": 160, "label": "south-80", "reviewed": True},
    ]
    assert env["rows"] == [
        {"region": "north", "amount": 120, "temp": "x"},
        {"region": "south", "amount": 80, "temp": "y"},
    ]


def test_sequence_record_field_verbs_accept_strings_and_missing_drops():
    env = run_source(
        """
rows = seq [{"region": "north", "amount": 120}]
result = rows
  |> drop_fields("missing")
  |> keep_fields("region")
""",
        filename="sequence_record_string_fields_test.pyplyne",
    )

    assert env["result"] == [{"region": "north"}]


def test_sequence_filter_accepts_bare_record_field_expressions():
    env = run_source(
        """
rows = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens", "qty": 2},
  {"item": "paper", "qty": 1},
]
result = rows
  |> filter(qty > 1)
  |> keep_fields(item)
  |> set_fields(buy = item == "pens")
""",
        filename="sequence_filter_bare_fields_test.pyplyne",
    )

    assert env["result"] == [
        {"item": "coffee", "buy": False},
        {"item": "pens", "buy": True},
    ]


def test_sequence_filter_still_accepts_direct_predicate_functions():
    def has_multiple_items(row):
        return row["qty"] > 1

    env = run_source(
        """
rows = seq [
  {"item": "coffee", "qty": 3},
  {"item": "paper", "qty": 1},
]
result = rows |> filter(has_multiple_items)
""",
        filename="sequence_filter_predicate_function_test.pyplyne",
        globals_dict={"has_multiple_items": has_multiple_items},
    )

    assert env["result"] == [{"item": "coffee", "qty": 3}]


def test_sequence_filter_missing_bare_record_fields_do_not_match():
    env = run_source(
        """
rows = seq [
  {"item": "coffee", "qty": 3},
  {"item": "pens"},
  {"item": "paper", "qty": 1},
]
result = rows |> filter(qty > 1)
""",
        filename="sequence_filter_missing_bare_field_test.pyplyne",
    )

    assert env["result"] == [{"item": "coffee", "qty": 3}]


def test_sequence_set_fields_missing_bare_record_field_comparisons_do_not_crash():
    env = run_source(
        """
rows = seq [
  {"item": "coffee"},
  {"qty": 2},
  {"item": "pens"},
]
result = rows |> set_fields(buy = item == "pens")
""",
        filename="sequence_set_fields_missing_comparison_test.pyplyne",
    )

    assert env["result"] == [
        {"item": "coffee", "buy": False},
        {"qty": 2, "buy": False},
        {"item": "pens", "buy": True},
    ]


def test_sequence_set_fields_missing_bare_record_field_arithmetic_still_errors():
    with pytest.raises(TypeError, match="_MissingField"):
        run_source(
            """
rows = seq [{"item": "coffee"}]
result = rows |> set_fields(double = qty * 2)
""",
            filename="sequence_set_fields_missing_arithmetic_test.pyplyne",
        )


def test_sequence_filter_bare_fields_can_read_object_attributes():
    class Order:
        def __init__(self, item, qty):
            self.item = item
            self.qty = qty

    orders = [Order("coffee", 3), Order("paper", 1), Order("pens", 2)]

    env = run_source(
        """
result = seq orders |> filter(qty > 1)
""",
        filename="sequence_filter_object_attributes_test.pyplyne",
        globals_dict={"orders": orders},
    )

    assert [order.item for order in env["result"]] == ["coffee", "pens"]


def test_sequence_filter_missing_object_attributes_do_not_match():
    class WithQty:
        qty = 2

    class WithoutQty:
        pass

    env = run_source(
        """
result = seq objects |> filter(qty > 1)
""",
        filename="sequence_filter_missing_object_attribute_test.pyplyne",
        globals_dict={"objects": [WithQty(), WithoutQty()]},
    )

    assert [type(item).__name__ for item in env["result"]] == ["WithQty"]


def test_sequence_filter_can_access_function_attributes_and_call_function_rows():
    def accepts_positive(value):
        return value > 0

    def rejects_positive(value):
        return value <= 0

    env = run_source(
        """
named = seq funcs |> filter(__name__ == "accepts_positive")
callable_rows = seq funcs |> filter(_(2))
""",
        filename="sequence_filter_function_rows_test.pyplyne",
        globals_dict={"funcs": [accepts_positive, rejects_positive]},
    )

    assert env["named"] == [accepts_positive]
    assert env["callable_rows"] == [accepts_positive]


def test_sequence_record_field_verbs_require_seq_pipelines():
    with pytest.raises(SyntaxError, match="set_fields is a seq verb"):
        run_source(
            """
rows = df [{"amount": 120}]
result = rows |> set_fields(reviewed=True)
""",
            filename="df_used_as_record_sequence_test.pyplyne",
        )


def test_tabular_bare_expressions_run_on_polars():
    env = run_source(
        """
rows = df [{"amount": 50}, {"amount": 150}]
result = rows
  |> where(amount > 100)
  |> mutate(double=amount * 2)
  |> select(amount, double)
""",
        filename="table_test.pyplyne",
    )

    assert isinstance(env["result"], pl.DataFrame)
    assert env["result"].to_dicts() == [{"amount": 150, "double": 300}]
    assert isinstance(env["rows"], pl.DataFrame)
    assert env["rows"].to_dicts() == [{"amount": 50}, {"amount": 150}]


def test_rhs_shape_annotations_normalize_values():
    env = run_source(
        """
rows = df [{"amount": 50}, {"amount": 150}]
row_dicts = rows |> to_rows()
table_again = row_dicts |> to_table()
""",
        filename="shape_normalization_test.pyplyne",
    )

    assert isinstance(env["rows"], pl.DataFrame)
    assert env["row_dicts"] == [{"amount": 50}, {"amount": 150}]
    assert isinstance(env["table_again"], pl.DataFrame)
    assert env["table_again"].to_dicts() == [{"amount": 50}, {"amount": 150}]


def test_seq_annotation_rejects_non_iterable_values_immediately():
    with pytest.raises(TypeError, match="seq annotation expects iterable data, got int"):
        run_source("nonsense = seq 42\n", filename="bad_seq_int_test.pyplyne")

    with pytest.raises(TypeError, match="seq annotation expects iterable data, got type"):
        run_source("nonsense = seq int\n", filename="bad_seq_type_test.pyplyne")


def test_seq_annotation_rejects_mapping_values_immediately():
    with pytest.raises(TypeError, match=r"seq annotation expects iterable data, got mapping"):
        run_source('row = seq {"amount": 120}\n', filename="bad_seq_mapping_test.pyplyne")


def test_df_annotation_reports_non_table_values_clearly():
    with pytest.raises(TypeError, match="df annotation expects table-shaped data, got int"):
        run_source("nonsense = df 42\n", filename="bad_df_int_test.pyplyne")


def test_df_annotation_accepts_imported_polars_dataframe_constructor():
    env = run_source(
        """
import polars as pl
sales = df pl.DataFrame([
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
])
result = sales
  |> where(amount > 100)
  |> select(region, amount)
""",
        filename="polars_constructor_test.pyplyne",
    )

    assert isinstance(env["sales"], pl.DataFrame)
    assert env["result"].to_dicts() == [
        {"region": "north", "amount": 120},
        {"region": "north", "amount": 220},
    ]


def test_df_annotation_converts_imported_pandas_dataframe_to_polars():
    env = run_source(
        """
import pandas as pd
sales = df pd.DataFrame([
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
])
result = sales
  |> where(amount > 100)
  |> mutate(double=amount * 2)
  |> select(region, amount, double)
""",
        filename="pandas_constructor_test.pyplyne",
    )

    assert isinstance(env["sales"], pl.DataFrame)
    assert env["result"].to_dicts() == [
        {"region": "north", "amount": 120, "double": 240},
        {"region": "north", "amount": 220, "double": 440},
    ]


def test_tabular_bare_boolean_expressions_use_polars_ops():
    env = run_source(
        """
rows = df [{"region": "north", "amount": 50}, {"region": "north", "amount": 150}, {"region": "south", "amount": 200}]
result = rows
  |> where(amount > 100 and region == "north")
  |> select(region, amount)
""",
        filename="boolean_table_test.pyplyne",
    )

    assert env["result"].to_dicts() == [{"region": "north", "amount": 150}]


def test_summarize_uses_polars_aggregations():
    env = run_source(
        """
rows = df [{"region": "north", "amount": 50}, {"region": "north", "amount": 150}, {"region": "south", "amount": 200}]
result = rows
  |> group_by(region)
  |> summarize(total=sum(amount), average=mean(amount))
""",
        filename="summarize_table_test.pyplyne",
    )

    assert sorted(env["result"].to_dicts(), key=lambda row: row["region"]) == [
        {"region": "north", "total": 200, "average": 100.0},
        {"region": "south", "total": 200, "average": 200.0},
    ]


def test_table_verbs_cover_arrange_and_all_aggregations():
    env = run_source(
        """
rows = df [
  {"region": "north", "amount": 50},
  {"region": "north", "amount": 150},
  {"region": "south", "amount": 200},
]
result = rows
  |> group_by(region)
  |> summarize(
    total=sum(amount),
    average=mean(amount),
    smallest=min(amount),
    largest=max(amount),
    rows=count(),
  )
  |> arrange(region, descending=True)
""",
        filename="all_table_verbs_test.pyplyne",
    )

    assert env["result"].to_dicts() == [
        {"region": "south", "total": 200, "average": 200.0, "smallest": 200, "largest": 200, "rows": 1},
        {"region": "north", "total": 200, "average": 100.0, "smallest": 50, "largest": 150, "rows": 2},
    ]


def test_group_by_without_summarize_has_clear_runtime_error():
    with pytest.raises(TypeError, match=r"group_by\(\.\.\.\) must be followed by summarize"):
        run_source(
            """
sales = df [{"region": "north", "amount": 120}]
grouped = sales |> group_by(region)
""",
            filename="unfinished_group_by_test.pyplyne",
        )


def test_defer_preserves_polars_lazy_plan():
    env = run_source(
        """
rows = df [{"amount": 50}, {"amount": 150}]
plan = defer rows
  |> where(amount > 100)
""",
        filename="defer_table_test.pyplyne",
    )

    assert isinstance(env["plan"], pl.LazyFrame)
    assert env["plan"].collect().to_dicts() == [{"amount": 150}]


def test_sequence_verbs_reject_df_pipelines():
    with pytest.raises(SyntaxError, match="map is a seq verb"):
        run_source(
            """
rows = df [{"amount": 50}, {"amount": 150}]
result = rows |> map(_["amount"])
""",
            filename="df_used_as_seq_test.pyplyne",
        )


def test_table_verbs_reject_seq_pipelines():
    with pytest.raises(SyntaxError, match="where is a df verb"):
        run_source(
            """
rows = seq [{"amount": 50}, {"amount": 150}]
result = rows |> where(amount > 100)
""",
            filename="seq_used_as_df_test.pyplyne",
        )


def test_shaped_pipeline_assignments_infer_final_variable_shape():
    env = run_source(
        """
numbers = seq [1, 2, 3]
result = numbers |> map(_ * 2)
"""
    )

    assert env["result"] == [2, 4, 6]


def test_pipeline_from_unshaped_variable_requires_rhs_shape_annotation():
    with pytest.raises(SyntaxError, match="map requires a known seq pipeline"):
        run_source(
            """
numbers = [1, 2, 3]
result = numbers |> map(_ * 2)
""",
            filename="undeclared_pipeline_assignment_test.pyplyne",
        )


def test_rhs_shape_annotation_can_seed_unshaped_pipeline_source():
    env = run_source(
        """
numbers = [1, 2, 3]
result = seq numbers |> map(_ * 2)
"""
    )

    assert env["result"] == [2, 4, 6]


def test_import_compiles_to_native_import_ast():
    module = compile_ast(parse_source("import math as m\nanswer = m.sqrt(81)\n"), filename="import_test.pyplyne")

    imports = list(iter_nodes(module, ast.Import))
    assert imports
    assert imports[0].names[0].name == "math"
    assert imports[0].names[0].asname == "m"


def test_imports_execute_for_import_and_from_import():
    env = run_source(
        """
import math as m
from pathlib import Path
answer = m.sqrt(81)
suffix = Path("data.csv").suffix
""",
        filename="import_execute_test.pyplyne",
    )

    assert env["answer"] == 9
    assert env["suffix"] == ".csv"


def test_read_csv_write_csv_collect_and_shape_conversions(tmp_path):
    input_path = tmp_path / "sales.csv"
    output_path = tmp_path / "summary.csv"
    input_path.write_text("region,amount\nnorth,120\nsouth,80\nnorth,220\n", encoding="utf-8")

    env = run_source(
        f"""
sales = df read_csv("{input_path}")
summary = sales
  |> where(amount > 100)
  |> group_by(region)
  |> summarize(total=sum(amount))
  |> arrange(region)
summary |> write_csv("{output_path}")
collected = summary |> collect()
rows = summary |> to_rows()
table = rows |> to_table()
""",
        filename="csv_io_test.pyplyne",
    )

    assert output_path.exists()
    assert env["summary"].to_dicts() == [{"region": "north", "total": 340}]
    assert isinstance(env["collected"], pl.DataFrame)
    assert env["collected"].to_dicts() == [{"region": "north", "total": 340}]
    assert env["rows"] == [{"region": "north", "total": 340}]
    assert isinstance(env["table"], pl.DataFrame)
    assert env["table"].to_dicts() == [{"region": "north", "total": 340}]
    assert pl.read_csv(output_path).to_dicts() == [{"region": "north", "total": 340}]


def test_read_write_json_and_parquet_helpers_preserve_df_pipelines(tmp_path):
    json_path = tmp_path / "sales.json"
    parquet_path = tmp_path / "summary.parquet"
    csv_path = tmp_path / "summary.csv"
    pl.DataFrame(
        [
            {"region": "north", "amount": 120, "discount": 10},
            {"region": "south", "amount": 80, "discount": 0},
            {"region": "north", "amount": 220, "discount": 20},
        ]
    ).write_json(json_path)

    env = run_source(
        f"""
sales = df read_json("{json_path}")
summary = sales
  |> where(amount > 100)
  |> mutate(net=amount - discount)
  |> select(region, amount, net)
  |> arrange(region)
summary
  |> write_parquet("{parquet_path}")
  |> write_csv("{csv_path}")
from_parquet = df read_parquet("{parquet_path}")
""",
        filename="json_parquet_io_test.pyplyne",
    )

    expected = [
        {"region": "north", "amount": 120, "net": 110},
        {"region": "north", "amount": 220, "net": 200},
    ]
    assert env["summary"].to_dicts() == expected
    assert env["from_parquet"].to_dicts() == expected
    assert pl.read_parquet(parquet_path).to_dicts() == expected
    assert pl.read_csv(csv_path).to_dicts() == expected


def test_read_write_excel_helpers_preserve_df_pipelines(tmp_path):
    pytest.importorskip("fastexcel")
    pytest.importorskip("xlsxwriter")

    input_path = tmp_path / "sales.xlsx"
    output_path = tmp_path / "large_sales.xlsx"
    pl.DataFrame(
        [
            {"region": "north", "amount": 120},
            {"region": "south", "amount": 80},
            {"region": "north", "amount": 220},
        ]
    ).write_excel(input_path)

    env = run_source(
        f"""
sales = df read_excel("{input_path}")
large_sales = sales
  |> where(amount > 100)
  |> select(region, amount)
large_sales |> write_excel("{output_path}")
roundtrip = df read_excel("{output_path}")
""",
        filename="excel_io_test.pyplyne",
    )

    expected = [
        {"region": "north", "amount": 120},
        {"region": "north", "amount": 220},
    ]
    assert env["large_sales"].to_dicts() == expected
    assert env["roundtrip"].to_dicts() == expected


def test_can_convert_shapes_within_one_pipeline():
    env = run_source(
        """
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
]
reviewed = sales
  |> where(amount > 100)
  |> to_rows()
  |> map(row => {
    "region": row["region"],
    "amount": row["amount"],
    "reviewed": True,
  })
  |> to_table()
  |> where(amount > 150)
  |> arrange(region)
""",
        filename="shape_conversion_pipeline_test.pyplyne",
    )

    assert env["reviewed"].to_dicts() == [
        {"region": "north", "amount": 220, "reviewed": True},
    ]


def test_can_convert_df_to_seq_and_continue_with_sequence_verbs():
    env = run_source(
        """
sales = df [
  {"region": "north", "amount": 120},
  {"region": "south", "amount": 80},
  {"region": "north", "amount": 220},
]
labels = sales
  |> where(amount > 100)
  |> to_rows()
  |> map(_["region"])
  |> filter(_ == "north")
""",
        filename="df_to_seq_pipeline_test.pyplyne",
    )

    assert env["labels"] == ["north", "north"]


def test_df_verbs_after_to_rows_require_to_table_first():
    with pytest.raises(SyntaxError, match="where is a df verb"):
        run_source(
            """
sales = df [{"amount": 120}, {"amount": 80}]
result = sales
  |> to_rows()
  |> where(amount > 100)
""",
            filename="missing_to_table_test.pyplyne",
        )


def test_sequence_verbs_after_to_table_require_to_rows_first():
    with pytest.raises(SyntaxError, match="map is a seq verb"):
        run_source(
            """
rows = seq [{"amount": 120}, {"amount": 80}]
result = rows
  |> to_table()
  |> map(_["amount"])
""",
            filename="missing_to_rows_test.pyplyne",
        )


def test_bare_tabular_expression_compiles_to_column_call():
    module = compile_ast(
        parse_source("rows = df [{\"amount\": 1}]\nresult = rows |> where(amount > 100)\n"),
        filename="expr_compile_test.pyplyne",
    )

    calls = [node for node in ast.walk(module) if isinstance(node, ast.Call)]
    assert any(isinstance(call.func, ast.Name) and call.func.id == "_col" for call in calls)


def test_traceback_uses_dsl_filename_and_line():
    source = """
numbers = seq [1, 2, 3]
result = numbers
  |> map(fn x: 10 / (x - 2))
"""

    with pytest.raises(ZeroDivisionError) as excinfo:
        run_source(source, filename="broken_pipeline.pyplyne")

    traceback = excinfo.traceback
    assert any(str(frame.path).endswith("broken_pipeline.pyplyne") and frame.lineno + 1 == 4 for frame in traceback)


def test_method_pipe_threads_value_as_receiver():
    env = run_source(
        """
text = "hello"
result = text
  |> .upper()
""",
        filename="method_test.pyplyne",
    )

    assert env["result"] == "HELLO"


def test_literals_indexing_attributes_constants_and_comments():
    env = run_source(
        """
# basic expression surface
rows = [{"name": "Ada", "score": 10, "active": True}, {"name": "Lin", "score": None, "active": False}]
first = rows[0]["name"]
is_active = rows[0]["active"] and not rows[1]["active"]
missing = rows[1]["score"]
""",
        filename="expression_surface_test.pyplyne",
    )

    assert env["first"] == "Ada"
    assert env["is_active"] is True
    assert env["missing"] is None


def test_full_language_tour_example_runs():
    output_path = Path("examples/full_language_tour_output.csv")
    if output_path.exists():
        output_path.unlink()

    env = run_file("examples/full_language_tour.pyplyne")

    assert env["sequence_total"] == 180
    assert isinstance(env["summary"], pl.DataFrame)
    assert isinstance(env["plan"], pl.LazyFrame)
    assert isinstance(env["summary_rows"], list)
    assert isinstance(env["summary_table"], pl.DataFrame)
    assert isinstance(env["reviewed_sales"], pl.DataFrame)
    assert "discount" in env["reviewed_sales"].columns
    assert output_path.exists()
    output_path.unlink()


def test_shape_conversions_example_runs():
    env = run_file("examples/shape_conversions.pyplyne")

    assert env["labels"] == ["north", "north"]
    assert env["reviewed"].to_dicts() == [
        {"region": "north", "amount": 120, "reviewed": True},
        {"region": "north", "amount": 220, "reviewed": True},
    ]


def test_record_fields_example_runs():
    env = run_file("examples/record_fields.pyplyne")

    assert env["with_fields"][0] == {
        "region": "north",
        "amount": 120,
        "discount": 10,
        "debug": "a",
        "net": 110,
        "reviewed": True,
        "label": "north-120",
    }
    assert "debug" not in env["without_debug"][0]
    assert env["projected"] == [
        {"region": "north", "amount": 120, "net": 110, "reviewed": True, "label": "north-120"},
        {"region": "south", "amount": 80, "net": 75, "reviewed": False, "label": "south-80"},
        {"region": "north", "amount": 220, "net": 200, "reviewed": True, "label": "north-220"},
    ]


def test_polars_constructor_example_runs():
    env = run_file("examples/polars_constructor.pyplyne")

    assert isinstance(env["sales"], pl.DataFrame)
    assert env["large_sales"].to_dicts() == [
        {"region": "north", "amount": 120},
        {"region": "north", "amount": 220},
    ]
