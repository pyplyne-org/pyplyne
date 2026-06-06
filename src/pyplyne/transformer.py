from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable, Optional, Union

from lark import Token, Tree


@dataclass(frozen=True)
class ImportAlias:
    name: str
    asname: Optional[str]


@dataclass(frozen=True)
class KeywordArg:
    name: str
    value: ast.expr


@dataclass(frozen=True)
class AttrTrailer:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class CallTrailer:
    args: list[ast.expr]
    keywords: list[ast.keyword]
    line: int
    column: int


@dataclass(frozen=True)
class SubscriptTrailer:
    index: ast.expr
    line: int
    column: int


@dataclass(frozen=True)
class MethodPipe:
    name: str
    args: list[ast.expr]
    keywords: list[ast.keyword]
    line: int
    column: int


TABULAR_VERBS = {"where", "mutate", "select", "group_by", "summarize", "arrange"}
SEQUENCE_LAMBDA_VERBS = {"map", "filter", "reduce"}
SEQUENCE_FIELD_UPDATE_VERBS = {"set_fields"}
SEQUENCE_FIELD_SELECT_VERBS = {"drop_fields", "keep_fields"}
SEQUENCE_RECORD_VERBS = SEQUENCE_FIELD_UPDATE_VERBS | SEQUENCE_FIELD_SELECT_VERBS
TABLE_READ_FUNCTIONS = {"read_csv", "read_json", "read_parquet", "read_excel"}
TABLE_WRITE_FUNCTIONS = {"write_csv", "write_json", "write_parquet", "write_excel"}
SEQ_PRESERVING_VERBS = {"map", "filter"} | SEQUENCE_RECORD_VERBS
SEQ_TERMINAL_VERBS = {"reduce"}
DF_VERBS = TABULAR_VERBS | {"collect"}
SEQ_VERBS = SEQ_PRESERVING_VERBS
BOTH_SHAPE_VERBS = TABLE_WRITE_FUNCTIONS
DF_TO_SEQ_VERBS = {"to_rows"}
SEQ_TO_DF_VERBS = {"to_table"}
DF_KIND = "df"
SEQ_KIND = "seq"
SCALAR_KIND = "scalar"
SHAPE_KINDS = {DF_KIND, SEQ_KIND}


def compile_ast(
    tree: Tree,
    filename: str = "<pyplyne>",
    symbol_kinds: Optional[dict[str, str]] = None,
) -> ast.Module:
    """Compile a PyPlyne parse tree into a Python AST module.

    Args:
        tree: Parse tree returned by `parse_source`.
        filename: Virtual filename copied into generated AST nodes.
        symbol_kinds: Optional shape registry used to validate `df` and `seq`
            pipelines across session runs.

    Returns:
        ast.Module: Python AST module that can be compiled with `compile`.

    Raises:
        SyntaxError: The parse tree contains an invalid PyPlyne construct.
    """

    module = AstBuilder(filename, symbol_kinds=symbol_kinds).build_module(tree)
    ast.fix_missing_locations(module)
    return module


class AstBuilder:
    def __init__(self, filename: str, symbol_kinds: Optional[dict[str, str]] = None) -> None:
        self.filename = filename
        self.symbol_kinds = symbol_kinds if symbol_kinds is not None else {}

    def build_module(self, tree: Tree) -> ast.Module:
        if tree.data != "start":
            self._fail(tree, "expected start tree")
        program = self._single_tree(tree, "program")
        body: list[ast.stmt] = []
        for statement in program.children:
            if not isinstance(statement, Tree) or statement.data == "statement_end":
                continue
            built = self._stmt(statement)
            if built is not None:
                body.append(built)
        return ast.Module(body=body, type_ignores=[])

    def _stmt(self, tree: Tree) -> Optional[ast.stmt]:
        if tree.data == "statement":
            inner = [child for child in tree.children if isinstance(child, Tree) and child.data != "statement_end"]
            if not inner:
                return None
            return self._stmt(inner[0])

        if tree.data == "import_stmt":
            aliases = [self._import_alias(child) for child in tree.children]
            node = ast.Import(
                names=[ast.alias(name=alias.name, asname=alias.asname) for alias in aliases]
            )
            return self._loc(node, tree)
        if tree.data == "from_import_stmt":
            module = self._dotted_name(tree.children[0])
            aliases = [self._import_alias(child) for child in tree.children[1:]]
            node = ast.ImportFrom(
                module=module,
                names=[ast.alias(name=alias.name, asname=alias.asname) for alias in aliases],
                level=0,
            )
            return self._loc(node, tree)
        if tree.data == "assignment":
            name_token = self._token(tree.children[0])
            value_tree = self._tree(tree.children[1])
            name = str(name_token)
            expression_kind = self._expr_kind(value_tree)
            value = self._expr(value_tree)
            if not self._is_defer_expr(value_tree):
                value = self._auto_collect(value)
            if expression_kind in SHAPE_KINDS:
                self.symbol_kinds[name] = expression_kind
            else:
                self.symbol_kinds.pop(name, None)
            target = ast.Name(id=str(name_token), ctx=ast.Store())
            self._loc_from_token(target, name_token)
            node = ast.Assign(targets=[target], value=value)
            return self._loc(node, tree)

        value = self._expr(tree)
        if not self._is_defer_expr(tree):
            value = self._auto_collect(value)
        node = ast.Expr(value=value)
        return self._loc(node, tree)

    def _expr(self, item: Union[Tree, Token, ast.expr]) -> ast.expr:
        if isinstance(item, ast.expr):
            return item
        if isinstance(item, Token):
            if item.type == "NAME":
                return self._loc_from_token(ast.Name(id=str(item), ctx=ast.Load()), item)
            self._fail(item, f"unexpected token {item.type}")

        if item.data == "shape_expr":
            shape_kind = self._shape_kind(self._token(item.children[0]))
            return self._shaped_expr(shape_kind, self._tree(item.children[1]))
        if item.data == "pipeline":
            return self._pipeline_expr(item)
        if item.data == "defer_expr":
            return self._expr(item.children[0])
        if item.data == "bool_or":
            return self._bool_op(ast.Or(), item)
        if item.data == "bool_and":
            return self._bool_op(ast.And(), item)
        if item.data == "not_expr":
            node = ast.UnaryOp(op=ast.Not(), operand=self._expr(item.children[0]))
            return self._loc(node, item)
        if item.data == "comparison":
            left = self._expr(item.children[0])
            ops = []
            comparators = []
            children = list(item.children[1:])
            for op_token, right in zip(children[0::2], children[1::2]):
                ops.append(self._cmp_op(self._token(op_token)))
                comparators.append(self._expr(right))
            if not ops:
                return left
            return self._loc(ast.Compare(left=left, ops=ops, comparators=comparators), item)
        if item.data in ("arith", "term"):
            return self._bin_ops(item)
        if item.data == "unary_expr":
            op_token = self._token(item.children[0])
            operand = self._expr(item.children[1])
            op = ast.UAdd() if str(op_token) == "+" else ast.USub()
            return self._loc(ast.UnaryOp(op=op, operand=operand), item)
        if item.data == "lambda_expr":
            params = self._lambda_params(item.children[0])
            body = self._expr(item.children[1])
            return self._lambda(params, body, item)
        if item.data == "arrow_lambda":
            params = self._lambda_param_target(self._tree(item.children[0]))
            body = self._expr(item.children[1])
            return self._lambda(params, body, item)
        if item.data == "primary":
            current = self._expr(item.children[0])
            for trailer in item.children[1:]:
                current = self._apply_trailer(current, self._trailer(trailer))
            return current
        if item.data == "identifier":
            return self._loc(ast.Name(id=str(self._token(item.children[0])), ctx=ast.Load()), item)
        if item.data == "string":
            return self._loc(ast.Constant(value=ast.literal_eval(str(item.children[0]))), item)
        if item.data == "number":
            return self._loc(ast.Constant(value=ast.literal_eval(str(item.children[0]))), item)
        if item.data == "true":
            return self._loc(ast.Constant(value=True), item)
        if item.data == "false":
            return self._loc(ast.Constant(value=False), item)
        if item.data == "none":
            return self._loc(ast.Constant(value=None), item)
        if item.data == "list_literal":
            args, keywords = self._args(item.children[0]) if item.children else ([], [])
            if keywords:
                self._fail(item, "list literals cannot contain keyword arguments")
            return self._loc(ast.List(elts=args, ctx=ast.Load()), item)
        if item.data == "tuple_literal":
            first = self._arg(self._tree(item.children[0]))
            if isinstance(first, KeywordArg):
                self._fail(item, "tuple literals cannot contain keyword arguments")
            args = [first]
            if len(item.children) > 1:
                rest, keywords = self._args(item.children[1])
                args.extend(rest)
            else:
                keywords = []
            if keywords:
                self._fail(item, "tuple literals cannot contain keyword arguments")
            return self._loc(ast.Tuple(elts=args, ctx=ast.Load()), item)
        if item.data == "dict_literal":
            keys = []
            values = []
            if item.children:
                for entry in self._tree(item.children[0]).children:
                    key, value = self._tree(entry).children
                    keys.append(self._expr(key))
                    values.append(self._expr(value))
            return self._loc(ast.Dict(keys=keys, values=values), item)

        self._fail(item, f"unsupported expression node {item.data}")

    def _pipe(
        self,
        value: ast.expr,
        current_kind: Optional[str],
        target: Union[Tree, Token],
    ) -> tuple[ast.expr, Optional[str]]:
        if isinstance(target, Token):
            func = self._loc_from_token(ast.Name(id=str(target), ctx=ast.Load()), target)
            next_kind = self._validate_verb_kind(current_kind, str(target), target)
            node = ast.Call(func=func, args=[value], keywords=[])
            return self._loc_from_token(node, target), next_kind

        if target.data == "identifier":
            name = self._token(target.children[0])
            func = self._loc(ast.Name(id=str(name), ctx=ast.Load()), target)
            next_kind = self._validate_verb_kind(current_kind, str(name), target)
            node = ast.Call(func=func, args=[value], keywords=[])
            return self._loc(node, target), next_kind

        if target.data == "method_pipe":
            method = self._method_pipe(target)
            func = ast.Attribute(value=value, attr=method.name, ctx=ast.Load())
            self._loc_at(func, method.line, method.column)
            node = ast.Call(func=func, args=method.args, keywords=method.keywords)
            return self._loc_at(node, method.line, method.column), current_kind

        call = self._expr(target)
        if not isinstance(call, ast.Call):
            self._fail(target, "pipeline target must be a function call, method call, or identifier")
        next_kind = self._validate_call_kind(current_kind, call, target)
        self._rewrite_pipe_call(call)
        call.args.insert(0, value)
        return call, next_kind

    def _shape_kind(self, token: Token) -> str:
        text = str(token)
        if text in SHAPE_KINDS:
            return text
        raise SyntaxError(f"{self.filename}:{token.line}:{token.column}: expected df or seq")

    def _pipeline_expr(self, item: Tree, initial_kind: Optional[str] = None) -> ast.expr:
        current = self._expr(item.children[0])
        current_kind = initial_kind if initial_kind is not None else self._expr_kind(self._tree(item.children[0]))
        if initial_kind is not None:
            current = self._coerce_declared_value(current, initial_kind)
        for target in item.children[1:]:
            current, current_kind = self._pipe(current, current_kind, target)
        return current

    def _shaped_expr(self, shape_kind: str, value_tree: Tree) -> ast.expr:
        if value_tree.data == "pipeline":
            return self._pipeline_expr(value_tree, initial_kind=shape_kind)
        return self._coerce_declared_value(self._expr(value_tree), shape_kind)

    def _expr_kind(self, item: Union[Tree, Token]) -> Optional[str]:
        if isinstance(item, Token):
            return self.symbol_kinds.get(str(item)) if item.type == "NAME" else None
        if item.data == "shape_expr":
            shape_kind = self._shape_kind(self._token(item.children[0]))
            value_tree = self._tree(item.children[1])
            if value_tree.data == "pipeline":
                return self._pipeline_kind(value_tree, initial_kind=shape_kind)
            return shape_kind
        if item.data == "defer_expr":
            return self._expr_kind(self._tree(item.children[0]))
        if item.data == "pipeline":
            return self._pipeline_kind(item)
        if item.data == "identifier":
            return self.symbol_kinds.get(str(self._token(item.children[0])))
        if item.data == "primary":
            return self._primary_kind(item)
        return None

    def _pipeline_kind(self, item: Tree, initial_kind: Optional[str] = None) -> Optional[str]:
        current_kind = initial_kind if initial_kind is not None else self._expr_kind(self._tree(item.children[0]))
        for target in item.children[1:]:
            current_kind = self._target_kind(current_kind, target)
        return current_kind

    def _primary_kind(self, tree: Tree) -> Optional[str]:
        if not tree.children:
            return None
        base = tree.children[0]
        if isinstance(base, Tree) and base.data == "identifier":
            base_name = str(self._token(base.children[0]))
            if len(tree.children) > 1:
                if base_name in TABLE_READ_FUNCTIONS and self._is_call_trailer(self._tree(tree.children[1])):
                    return DF_KIND
                if base_name == "to_table" and self._is_call_trailer(self._tree(tree.children[1])):
                    return DF_KIND
                if base_name == "to_rows" and self._is_call_trailer(self._tree(tree.children[1])):
                    return SEQ_KIND
            return self.symbol_kinds.get(base_name)
        return None

    def _is_call_trailer(self, tree: Tree) -> bool:
        return tree.data == "call_trailer"

    def _target_kind(self, current_kind: Optional[str], target: Union[Tree, Token]) -> Optional[str]:
        if isinstance(target, Token):
            return self._validate_verb_kind(current_kind, str(target), target)
        if target.data == "identifier":
            return self._validate_verb_kind(current_kind, str(self._token(target.children[0])), target)
        if target.data == "method_pipe":
            return current_kind
        call = self._expr(target)
        if not isinstance(call, ast.Call):
            self._fail(target, "pipeline target must be a function call, method call, or identifier")
        return self._validate_call_kind(current_kind, call, target)

    def _validate_call_kind(
        self,
        current_kind: Optional[str],
        call: ast.Call,
        item: Union[Tree, Token],
    ) -> Optional[str]:
        if not isinstance(call.func, ast.Name):
            return current_kind
        return self._validate_verb_kind(current_kind, call.func.id, item)

    def _validate_verb_kind(
        self,
        current_kind: Optional[str],
        verb: str,
        item: Union[Tree, Token],
    ) -> Optional[str]:
        if verb in DF_TO_SEQ_VERBS:
            self._require_kind(current_kind, DF_KIND, verb, item)
            return SEQ_KIND
        if verb in SEQ_TO_DF_VERBS:
            self._require_kind(current_kind, SEQ_KIND, verb, item)
            return DF_KIND
        if verb in DF_VERBS:
            self._require_kind(current_kind, DF_KIND, verb, item)
            return DF_KIND
        if verb in SEQ_TERMINAL_VERBS:
            self._require_kind(current_kind, SEQ_KIND, verb, item)
            return SCALAR_KIND
        if verb in SEQ_VERBS:
            self._require_kind(current_kind, SEQ_KIND, verb, item)
            return SEQ_KIND
        if verb in BOTH_SHAPE_VERBS:
            if current_kind not in SHAPE_KINDS:
                self._fail(item, f"{verb} requires a df or seq pipeline")
            return current_kind
        return current_kind

    def _require_kind(
        self,
        actual_kind: Optional[str],
        expected_kind: str,
        verb: str,
        item: Union[Tree, Token],
    ) -> None:
        if actual_kind is None:
            self._fail(item, f"{verb} requires a known {expected_kind} pipeline")
        if actual_kind != expected_kind:
            self._fail(item, f"{verb} is a {expected_kind} verb, but the current pipeline is {actual_kind}")

    def _rewrite_pipe_call(self, call: ast.Call) -> None:
        self._rewrite_sequence_call(call)
        self._rewrite_tabular_call(call)

    def _rewrite_sequence_call(self, call: ast.Call) -> None:
        if not isinstance(call.func, ast.Name):
            return

        if call.func.id in SEQUENCE_FIELD_UPDATE_VERBS:
            self._rewrite_sequence_field_update_call(call)
            return
        if call.func.id in SEQUENCE_FIELD_SELECT_VERBS:
            self._rewrite_sequence_field_select_call(call)
            return
        if call.func.id == "filter":
            self._rewrite_sequence_filter_call(call)
            return
        if call.func.id not in SEQUENCE_LAMBDA_VERBS:
            return

        call.args = [self._placeholder_lambda(arg) for arg in call.args]
        call.keywords = [
            ast.keyword(arg=keyword.arg, value=self._placeholder_lambda(keyword.value))
            for keyword in call.keywords
        ]

    def _rewrite_sequence_filter_call(self, call: ast.Call) -> None:
        call.args = [self._sequence_filter_predicate(arg) for arg in call.args]
        call.keywords = [
            ast.keyword(arg=keyword.arg, value=self._sequence_filter_predicate(keyword.value))
            for keyword in call.keywords
        ]

    def _sequence_filter_predicate(self, expr: ast.expr) -> ast.expr:
        if isinstance(expr, ast.Lambda):
            return expr
        if PlaceholderFinder.find(expr):
            return self._placeholder_lambda(expr)
        if isinstance(expr, ast.Name):
            return expr

        rewriter = RowExprRewriter()
        return self._row_lambda(rewriter.visit(expr), expr)

    def _rewrite_sequence_field_update_call(self, call: ast.Call) -> None:
        if call.args:
            arg = call.args[0]
            raise SyntaxError(
                f"{self.filename}:{arg.lineno}:{arg.col_offset + 1}: "
                "set_fields only accepts keyword field assignments"
            )

        rewriter = RowExprRewriter()
        call.keywords = [
            ast.keyword(arg=keyword.arg, value=self._row_lambda(rewriter.visit(keyword.value), keyword.value))
            for keyword in call.keywords
        ]

    def _rewrite_sequence_field_select_call(self, call: ast.Call) -> None:
        if call.keywords:
            keyword = call.keywords[0]
            raise SyntaxError(
                f"{self.filename}:{keyword.value.lineno}:{keyword.value.col_offset + 1}: "
                f"{call.func.id} only accepts field names"
            )
        call.args = [self._field_name_expr(arg) for arg in call.args]

    def _row_lambda(self, body: ast.expr, original: ast.expr) -> ast.Lambda:
        if isinstance(original, ast.Lambda):
            return original
        return self._lambda_at(["row"], body, original.lineno, original.col_offset + 1)

    def _field_name_expr(self, expr: ast.expr) -> ast.expr:
        if isinstance(expr, ast.Name):
            return ast.copy_location(ast.Constant(value=expr.id), expr)
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return expr
        raise SyntaxError(
            f"{self.filename}:{expr.lineno}:{expr.col_offset + 1}: "
            "field names must be bare names or strings"
        )

    def _rewrite_tabular_call(self, call: ast.Call) -> None:
        if not isinstance(call.func, ast.Name) or call.func.id not in TABULAR_VERBS:
            return

        converter = TableExprRewriter()
        call.args = [converter.visit(arg) for arg in call.args]
        call.keywords = [
            ast.keyword(arg=keyword.arg, value=converter.visit(keyword.value))
            for keyword in call.keywords
        ]

    def _placeholder_lambda(self, expr: ast.expr) -> ast.expr:
        if isinstance(expr, ast.Lambda):
            return expr

        placeholders = PlaceholderFinder.find(expr)
        if not placeholders:
            return expr

        if "_" in placeholders and len(placeholders) > 1:
            raise SyntaxError(
                f"{self.filename}:{expr.lineno}:{expr.col_offset + 1}: "
                "cannot mix _ with numbered placeholders"
            )

        if "_" in placeholders:
            params = ["_"]
        else:
            indices = sorted(int(name[1:]) for name in placeholders)
            expected = list(range(1, indices[-1] + 1))
            if indices != expected:
                raise SyntaxError(
                    f"{self.filename}:{expr.lineno}:{expr.col_offset + 1}: "
                    "numbered placeholders must start at _1 and be consecutive"
                )
            params = [f"_{index}" for index in indices]

        return self._lambda_at(params, expr, expr.lineno, expr.col_offset + 1)

    def _bool_op(self, op: ast.boolop, tree: Tree) -> ast.expr:
        values = [self._expr(child) for child in tree.children]
        if len(values) == 1:
            return values[0]
        return self._loc(ast.BoolOp(op=op, values=values), tree)

    def _bin_ops(self, tree: Tree) -> ast.expr:
        current = self._expr(tree.children[0])
        children = list(tree.children[1:])
        for op_token, right in zip(children[0::2], children[1::2]):
            current = self._loc(
                ast.BinOp(left=current, op=self._bin_op(self._token(op_token)), right=self._expr(right)),
                tree,
            )
        return current

    def _apply_trailer(
        self, value: ast.expr, trailer: Union[AttrTrailer, CallTrailer, SubscriptTrailer]
    ) -> ast.expr:
        if isinstance(trailer, AttrTrailer):
            node = ast.Attribute(value=value, attr=trailer.name, ctx=ast.Load())
            return self._loc_at(node, trailer.line, trailer.column)
        if isinstance(trailer, CallTrailer):
            node = ast.Call(func=value, args=trailer.args, keywords=trailer.keywords)
            return self._loc_at(node, trailer.line, trailer.column)
        node = ast.Subscript(value=value, slice=trailer.index, ctx=ast.Load())
        return self._loc_at(node, trailer.line, trailer.column)

    def _trailer(self, tree: Tree) -> Union[AttrTrailer, CallTrailer, SubscriptTrailer]:
        if tree.data == "attr_trailer":
            return AttrTrailer(str(self._token(tree.children[0])), tree.meta.line, tree.meta.column)
        if tree.data == "call_trailer":
            args, keywords = self._args(tree.children[0]) if tree.children else ([], [])
            return CallTrailer(args, keywords, tree.meta.line, tree.meta.column)
        if tree.data == "subscript_trailer":
            return SubscriptTrailer(self._expr(tree.children[0]), tree.meta.line, tree.meta.column)
        self._fail(tree, f"unsupported trailer {tree.data}")

    def _method_pipe(self, tree: Tree) -> MethodPipe:
        name = str(self._token(tree.children[0]))
        args, keywords = self._args(tree.children[1]) if len(tree.children) > 1 else ([], [])
        return MethodPipe(name, args, keywords, tree.meta.line, tree.meta.column)

    def _args(self, tree: Tree) -> tuple:
        args: list[ast.expr] = []
        keywords: list[ast.keyword] = []
        for child in tree.children:
            arg = self._arg(self._tree(child))
            if isinstance(arg, KeywordArg):
                keywords.append(ast.keyword(arg=arg.name, value=arg.value))
            else:
                if keywords:
                    self._fail(child, "positional arguments cannot follow keyword arguments")
                args.append(arg)
        return args, keywords

    def _arg(self, tree: Tree) -> Union[ast.expr, KeywordArg]:
        if tree.data == "keyword_arg":
            return KeywordArg(str(self._token(tree.children[0])), self._expr(tree.children[1]))
        if tree.data == "positional_arg":
            return self._expr(tree.children[0])
        self._fail(tree, f"unsupported argument {tree.data}")

    def _import_alias(self, tree: Tree) -> ImportAlias:
        dotted = self._dotted_name(tree.children[0])
        asname = str(self._token(tree.children[1])) if len(tree.children) > 1 else None
        return ImportAlias(dotted, asname)

    def _dotted_name(self, tree: Tree) -> str:
        return ".".join(str(self._token(child)) for child in tree.children)

    def _lambda_params(self, tree: Tree) -> list[str]:
        return [str(self._token(child)) for child in tree.children]

    def _lambda_param_target(self, tree: Tree) -> list[str]:
        if tree.data == "lambda_param_name":
            return [str(self._token(tree.children[0]))]
        if tree.data == "lambda_params":
            return self._lambda_params(tree)
        self._fail(tree, f"unsupported lambda parameter target {tree.data}")

    def _is_defer_expr(self, tree: Tree) -> bool:
        return tree.data == "defer_expr"

    def _auto_collect(self, value: ast.expr) -> ast.expr:
        node = ast.Call(func=ast.Name(id="_auto", ctx=ast.Load()), args=[value], keywords=[])
        return self._loc_at(node, value.lineno, value.col_offset + 1)

    def _coerce_declared_value(self, value: ast.expr, declared_kind: str) -> ast.expr:
        func_name = "_as_df" if declared_kind == DF_KIND else "_as_seq"
        node = ast.Call(func=ast.Name(id=func_name, ctx=ast.Load()), args=[value], keywords=[])
        return self._loc_at(node, value.lineno, value.col_offset + 1)

    def _lambda(self, params: list[str], body: ast.expr, tree: Tree) -> ast.Lambda:
        return self._lambda_at(params, body, tree.meta.line, tree.meta.column)

    def _lambda_at(self, params: list[str], body: ast.expr, line: int, column: int) -> ast.Lambda:
        args = ast.arguments(
            posonlyargs=[],
            args=[self._loc_at(ast.arg(arg=name), line, column) for name in params],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        return self._loc_at(ast.Lambda(args=args, body=body), line, column)

    def _cmp_op(self, token: Token) -> ast.cmpop:
        return {
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "<=": ast.LtE(),
            ">=": ast.GtE(),
            "<": ast.Lt(),
            ">": ast.Gt(),
        }[str(token)]

    def _bin_op(self, token: Token) -> ast.operator:
        return {
            "+": ast.Add(),
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.Div(),
            "//": ast.FloorDiv(),
            "%": ast.Mod(),
        }[str(token)]

    def _single_tree(self, tree: Tree, data: str) -> Tree:
        children = [child for child in tree.children if isinstance(child, Tree) and child.data == data]
        if len(children) != 1:
            self._fail(tree, f"expected one {data} child")
        return children[0]

    def _tree(self, item: Union[Tree, Token]) -> Tree:
        if not isinstance(item, Tree):
            self._fail(item, "expected tree")
        return item

    def _token(self, item: Union[Tree, Token]) -> Token:
        if not isinstance(item, Token):
            self._fail(item, "expected token")
        return item

    def _loc(self, node: ast.AST, tree: Tree) -> ast.AST:
        return self._loc_at(node, tree.meta.line, tree.meta.column)

    def _loc_from_token(self, node: ast.AST, token: Token) -> ast.AST:
        return self._loc_at(node, token.line, token.column)

    def _loc_at(self, node: ast.AST, line: int, column: int) -> ast.AST:
        node.lineno = line
        node.col_offset = max(column - 1, 0)
        node.end_lineno = line
        node.end_col_offset = max(column, 0)
        return node

    def _fail(self, item: Union[Tree, Token], message: str) -> None:
        line = getattr(getattr(item, "meta", None), "line", None) or getattr(item, "line", None)
        column = getattr(getattr(item, "meta", None), "column", None) or getattr(item, "column", None)
        location = f"{self.filename}:{line}:{column}" if line and column else self.filename
        raise SyntaxError(f"{location}: {message}")


class TableExprRewriter(ast.NodeTransformer):
    """Rewrite dplyr-style bare identifiers into Polars column expressions."""

    AGGREGATORS = {"sum", "mean", "min", "max", "count"}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if not isinstance(node.ctx, ast.Load):
            return node
        if node.id in {"True", "False", "None"}:
            return node
        return self._copy_location(
            ast.Call(
                func=ast.Name(id="_col", ctx=ast.Load()),
                args=[ast.Constant(value=node.id)],
                keywords=[],
            ),
            node,
        )

    def visit_Call(self, node: ast.Call) -> ast.AST:
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            node.args = [self.visit(arg) for arg in node.args]
            node.keywords = [
                ast.keyword(arg=keyword.arg, value=self.visit(keyword.value))
                for keyword in node.keywords
            ]
            if func_name in self.AGGREGATORS:
                return self._copy_location(
                    ast.Call(
                        func=ast.Name(id=f"_{func_name}", ctx=ast.Load()),
                        args=node.args,
                        keywords=node.keywords,
                    ),
                    node,
                )
            return node

        node.func = self.visit(node.func)
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [
            ast.keyword(arg=keyword.arg, value=self.visit(keyword.value))
            for keyword in node.keywords
        ]
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        values = [self.visit(value) for value in node.values]
        op: ast.operator = ast.BitAnd() if isinstance(node.op, ast.And) else ast.BitOr()
        current = values[0]
        for value in values[1:]:
            current = self._copy_location(ast.BinOp(left=current, op=op, right=value), node)
        return current

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        node.operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return self._copy_location(ast.UnaryOp(op=ast.Invert(), operand=node.operand), node)
        return node

    def _copy_location(self, new_node: ast.AST, old_node: ast.AST) -> ast.AST:
        return ast.copy_location(new_node, old_node)


class RowExprRewriter(ast.NodeTransformer):
    """Rewrite bare row field names into runtime field lookups."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if not isinstance(node.ctx, ast.Load):
            return node
        return self._copy_location(
            ast.Call(
                func=ast.Name(id="_field", ctx=ast.Load()),
                args=[
                    ast.Name(id="row", ctx=ast.Load()),
                    ast.Constant(value=node.id),
                ],
                keywords=[],
            ),
            node,
        )

    def visit_Call(self, node: ast.Call) -> ast.AST:
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [
            ast.keyword(arg=keyword.arg, value=self.visit(keyword.value))
            for keyword in node.keywords
        ]
        return node

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        return node

    def _copy_location(self, new_node: ast.AST, old_node: ast.AST) -> ast.AST:
        return ast.copy_location(new_node, old_node)


class PlaceholderFinder(ast.NodeVisitor):
    def __init__(self) -> None:
        self.placeholders: set[str] = set()

    @classmethod
    def find(cls, node: ast.AST) -> set[str]:
        finder = cls()
        finder.visit(node)
        return finder.placeholders

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "_" or (node.id.startswith("_") and node.id[1:].isdigit()):
            self.placeholders.add(node.id)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def iter_nodes(tree: ast.AST, node_type: type[ast.AST]) -> Iterable[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, node_type):
            yield node
