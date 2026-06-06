# tree-sitter-pyplyne

Tree-sitter grammar for PyPlyne.

This parser is for editor integrations such as Neovim highlighting and
structural navigation. It tracks the PyPlyne language surface in
`src/pyplyne/grammar.lark`, but the runtime parser remains Lark.

## Files

- `grammar.js`: Tree-sitter grammar source.
- `queries/highlights.scm`: Neovim Tree-sitter highlight captures.
- `test/corpus/basic.txt`: Tree-sitter corpus smoke tests.

## Generate And Test

```bash
npx --yes tree-sitter-cli@0.26.9 generate
npx --yes tree-sitter-cli@0.26.9 test
```

