# pyplyne.nvim

Neovim support for `.pyplyne` files.

This plugin is currently installed from this repository. Package-manager
publishing is pending.

It registers the `pyplyne` filetype, wires the local Tree-sitter grammar into
`nvim-treesitter`, provides highlight/indent queries, and adds interactive
commands backed by `pyplyne serve`.

The Tree-sitter grammar lives in `tree-sitter-pyplyne/`. The runtime parser
remains the Lark grammar in `src/pyplyne/grammar.lark`.

## Requirements

- Neovim 0.10+
- `nvim-treesitter`
- `node`/`npm`, because the local parser is generated from `grammar.js`
- a C compiler available on `PATH`
- `curl`, used by session health and shape checks
- the PyPlyne CLI available from the Neovim working directory

## LazyVim Install

Install PyPlyne in the project where you write `.pyplyne` files first. The
plugin runs `uv run pyplyne` by default.

Create `~/.config/nvim/lua/plugins/pyplyne.lua`:

```lua
return {
  {
    dir = "/path/to/pyplyne/editors/nvim-pyplyne",
    name = "pyplyne.nvim",
    lazy = false,
    opts = {},
    config = function(_, opts)
      require("pyplyne").setup(opts)
    end,
  },
}
```

Then run:

```vim
:TSInstall pyplyne
```

`lazy = false` lets the plugin register `.pyplyne` filetype detection and the
parser entry before you open a PyPlyne file.

If `pyplyne` is installed directly on `PATH`, configure:

```lua
opts = {
  executable = "pyplyne",
  executable_args = {},
}
```

Mason does not install Tree-sitter parsers. Use `nvim-treesitter` to build the
PyPlyne parser. Mason is only relevant if you choose to install helper tools
such as `tree-sitter-cli` through Mason instead of npm or your system package
manager.

## Commands

| Command | Purpose |
| --- | --- |
| `:PyplyneStart` | Start `pyplyne serve`, or connect to an already healthy session. |
| `:PyplyneStop` | Stop the session process started by this Neovim instance. |
| `:PyplyneRunLine` | Send the current line to the active session. |
| `:PyplyneRunSelection` | Send the visual selection to the active session. |
| `:PyplyneRunBlock` | Send the current blank-line-separated block. |
| `:PyplyneRunAssignment` | Run the current assignment block and then show the assigned value. |
| `:PyplyneRunFile` | Send the whole file to the active session. |
| `:PyplyneShapes` | Print known session shapes. |

## Default Keymaps

These mappings are buffer-local for `pyplyne` files:

| Keymap | Mode | Action |
| --- | --- | --- |
| `<leader>pl` | Normal | Run current line. |
| `<leader>pr` | Visual | Run selected source. |
| `<leader>pb` | Normal | Run current block. |
| `<leader>pa` | Normal | Run current assignment and show the assigned value. |
| `<leader>pf` | Normal | Run current file. |
| `<leader>ps` | Normal | Show session shapes. |
| `<leader>pS` | Normal | Start session. |
| `<leader>px` | Normal | Stop session. |

Terminal Neovim cannot reliably receive every `Ctrl+Enter` or
`Ctrl+Shift+Enter` combination across terminals, so the plugin uses leader
mappings by default. Override them through `opts.keymaps`:

```lua
opts = {
  keymaps = {
    run_block = "<leader><cr>",
    run_assignment = "<leader>p=",
  },
}
```

Set any mapping to `false` to disable it.

## Parser Only

If you do not want the full plugin, add a custom parser entry to your Neovim
config:

```lua
local parser_config = require("nvim-treesitter.parsers").get_parser_configs()

parser_config.pyplyne = {
  install_info = {
    url = "/path/to/pyplyne/editors/nvim-pyplyne/tree-sitter-pyplyne",
    files = { "src/parser.c" },
    generate_requires_npm = true,
    requires_generate_from_grammar = true,
  },
  filetype = "pyplyne",
}

vim.filetype.add({
  extension = {
    pyplyne = "pyplyne",
  },
})
```

Then run:

```vim
:TSInstall pyplyne
```

## Validate The Grammar

From this repository:

```bash
cd editors/nvim-pyplyne/tree-sitter-pyplyne
npx --yes tree-sitter-cli@0.26.9 generate
npx --yes tree-sitter-cli@0.26.9 test
```
