(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory((root && root.Prism) || require('prismjs'));
  } else {
    factory(root.Prism);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Prism) {
  if (!Prism || !Prism.languages) {
    return undefined;
  }

  const identifier = /[A-Za-z_]\w*/;
  const pipelineVerbs = [
    'arrange',
    'collect',
    'drop_fields',
    'filter',
    'group_by',
    'keep_fields',
    'map',
    'mutate',
    'reduce',
    'select',
    'set_fields',
    'summarize',
    'to_rows',
    'to_table',
    'where',
    'write_csv',
    'write_excel',
    'write_json',
    'write_parquet',
  ].join('|');
  const ioHelpers = [
    'read_csv',
    'read_excel',
    'read_json',
    'read_parquet',
    'write_csv',
    'write_excel',
    'write_json',
    'write_parquet',
  ].join('|');
  const aggregations = ['count', 'max', 'mean', 'min', 'sum'].join('|');

  Prism.languages.pyplyne = {
    comment: {
      pattern: /#.*/,
      greedy: true,
    },
    string: {
      pattern: /(["'])(?:\\[\s\S]|(?!\1)[^\\\r\n])*\1/,
      greedy: true,
    },
    'shape-keyword': {
      pattern: /\b(?:df|seq)\b/,
      alias: 'keyword',
    },
    keyword: /\b(?:and|as|defer|False|fn|from|import|None|not|or|True)\b/,
    function: [
      {
        pattern: new RegExp(`\\b(?:${pipelineVerbs})\\b(?=\\s*\\()`),
        alias: 'function',
      },
      {
        pattern: new RegExp(`\\b(?:${ioHelpers}|${aggregations})\\b(?=\\s*\\()`),
        alias: 'function',
      },
    ],
    'lambda-parameter': {
      pattern: /\b_(?:\d+)?\b/,
      alias: 'parameter',
    },
    number: /\b[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?\b/i,
    operator: /\|>|=>|==|!=|<=|>=|\/\/|[-+*/%=<>]|\./,
    punctuation: /[()[\]{},:]/,
    variable: identifier,
  };

  return Prism.languages.pyplyne;
});
