[
  "import"
  "from"
  "as"
] @keyword.import

[
  "fn"
  "=>"
] @keyword.function

[
  "defer"
] @keyword.modifier

(shape) @type

(boolean) @boolean
(none) @constant.builtin
(number) @number
(string) @string
(comment) @comment

[
  "and"
  "or"
  "not"
] @keyword.operator

[
  "="
  ":"
  "."
  ","
] @operator

(pipe_operator) @operator
(comparison_operator) @operator
(add_operator) @operator
(multiply_operator) @operator

(identifier) @variable

(lambda_parameters (identifier) @variable.parameter)
(lambda_parameter_target (identifier) @variable.parameter)

((identifier) @variable.builtin
  (#match? @variable.builtin "^_[0-9]*$"))

(import_alias (dotted_name) @module)
(from_import_statement (dotted_name) @module)

(method_pipe
  name: (identifier) @function.method)

(pipeline
  (identifier) @function
  (trailer
    (argument_list)))

(trailer
  attribute: (identifier) @property)

(keyword_argument
  name: (identifier) @variable.parameter)

((identifier) @function.builtin
  (#any-of? @function.builtin
    "where"
    "select"
    "mutate"
    "group_by"
    "summarize"
    "arrange"
    "read_csv"
    "write_csv"
    "to_rows"
    "to_table"
    "map"
    "filter"
    "reduce"
    "set_fields"
    "drop_fields"
    "keep_fields"
    "collect"))

