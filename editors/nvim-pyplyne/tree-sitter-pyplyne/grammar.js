const PREC = {
  or: 1,
  and: 2,
  not: 3,
  compare: 4,
  add: 5,
  multiply: 6,
  unary: 7,
  call: 8,
};

module.exports = grammar({
  name: "pyplyne",

  extras: ($) => [/[ \t]/, $.comment],

  word: ($) => $.identifier,

  conflicts: ($) => [
    [$.lambda_parameters, $._base],
  ],

  rules: {
    source_file: ($) =>
      seq(
        repeat($.line),
        optional($.statement),
      ),

    line: ($) => choice(seq($.statement, $._newline), $._newline),

    statement: ($) =>
      choice(
        $.import_statement,
        $.from_import_statement,
        $.assignment,
        $.expression_statement,
      ),

    import_statement: ($) =>
      seq("import", $.import_alias, repeat(seq(",", $.import_alias))),

    from_import_statement: ($) =>
      seq("from", $.dotted_name, "import", $.import_alias, repeat(seq(",", $.import_alias))),

    import_alias: ($) => seq($.dotted_name, optional(seq("as", $.identifier))),

    assignment: ($) =>
      seq(field("name", $.identifier), "=", field("value", $.expression)),

    expression_statement: ($) => $.expression,

    expression: ($) =>
      choice(
        $.shape_expression,
        $.defer_expression,
        $.lambda_expression,
        $.arrow_lambda,
        $.pipeline,
      ),

    shape_expression: ($) =>
      seq(field("shape", $.shape), field("value", $.expression)),

    defer_expression: ($) => seq("defer", field("value", $.expression)),

    pipeline: ($) =>
      prec.dynamic(1, prec.left(seq(
        $._bool_or,
        repeat(seq($.pipe_operator, optional($._newline), $.pipe_target)),
      ))),

    pipe_target: ($) => choice($.method_pipe, $._primary),

    method_pipe: ($) =>
      seq(".", field("name", $.identifier), field("arguments", $.argument_list)),

    _bool_or: ($) =>
      prec.left(PREC.or, seq($._bool_and, repeat(seq("or", $._bool_and)))),

    _bool_and: ($) =>
      prec.left(PREC.and, seq($._bool_not, repeat(seq("and", $._bool_not)))),

    _bool_not: ($) =>
      choice(prec(PREC.not, seq("not", $._bool_not)), $._comparison),

    _comparison: ($) =>
      prec.left(PREC.compare, seq($._arith, repeat(seq($.comparison_operator, $._arith)))),

    _arith: ($) =>
      prec.left(PREC.add, seq($._term, repeat(seq($.add_operator, $._term)))),

    _term: ($) =>
      prec.left(PREC.multiply, seq($._factor, repeat(seq($.multiply_operator, $._factor)))),

    _factor: ($) =>
      choice(prec(PREC.unary, seq($.add_operator, $._factor)), $._primary),

    lambda_expression: ($) =>
      seq("fn", field("parameters", $.lambda_parameters), ":", field("body", $.expression)),

    arrow_lambda: ($) =>
      seq(field("parameters", $.lambda_parameter_target), "=>", field("body", $.expression)),

    lambda_parameter_target: ($) =>
      choice($.identifier, seq("(", $.lambda_parameters, ")")),

    lambda_parameters: ($) => seq($.identifier, repeat(seq(",", $.identifier))),

    _primary: ($) =>
      prec.left(PREC.call, seq($._base, repeat($.trailer))),

    _base: ($) =>
      choice(
        $.literal,
        $.identifier,
        $.list_literal,
        $.tuple_literal,
        $.dict_literal,
        $.parenthesized_expression,
      ),

    parenthesized_expression: ($) => seq("(", $.expression, ")"),

    trailer: ($) =>
      choice(
        seq(".", field("attribute", $.identifier)),
        $.argument_list,
        seq("[", optional($._newline), $.expression, optional($._newline), "]"),
      ),

    argument_list: ($) =>
      seq(
        "(",
        optional($._newline),
        optional(seq($.argument, repeat(seq(optional($._newline), ",", optional($._newline), $.argument)), optional(","))),
        optional($._newline),
        ")",
      ),

    argument: ($) => choice($.keyword_argument, $.expression),

    keyword_argument: ($) =>
      seq(field("name", $.identifier), "=", field("value", $.expression)),

    list_literal: ($) =>
      seq(
        "[",
        optional($._newline),
        optional(seq($.argument, repeat(seq(optional($._newline), ",", optional($._newline), $.argument)), optional(","))),
        optional($._newline),
        "]",
      ),

    tuple_literal: ($) =>
      seq(
        "(",
        $.argument,
        optional($._newline),
        ",",
        optional($._newline),
        optional(seq($.argument, repeat(seq(optional($._newline), ",", optional($._newline), $.argument)), optional(","))),
        optional($._newline),
        ")",
      ),

    dict_literal: ($) =>
      seq(
        "{",
        optional($._newline),
        optional(seq($.dict_entry, repeat(seq(optional($._newline), ",", optional($._newline), $.dict_entry)), optional(","))),
        optional($._newline),
        "}",
      ),

    dict_entry: ($) => seq(field("key", $.expression), ":", field("value", $.expression)),

    literal: ($) => choice($.string, $.number, $.boolean, $.none),

    boolean: () => choice("True", "False"),

    none: () => "None",

    dotted_name: ($) => seq($.identifier, repeat(seq(".", $.identifier))),

    shape: () => choice("df", "seq"),

    comparison_operator: () => choice("==", "!=", "<=", ">=", "<", ">"),

    pipe_operator: () => token(prec(1, /\r?\n[ \t]*\|>|\|>/)),

    add_operator: () => choice("+", "-"),

    multiply_operator: () => choice("//", "*", "/", "%"),

    identifier: () => /[A-Za-z_][A-Za-z0-9_]*/,

    number: () => /[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/,

    string: () =>
      choice(
        /"([^"\\]|\\.)*"/,
        /'([^'\\]|\\.)*'/,
      ),

    comment: () => /#[^\n]*/,

    _newline: () => /(\r?\n)+/,
  },
});
