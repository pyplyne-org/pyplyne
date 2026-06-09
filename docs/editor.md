---
title: Editor Support
description: VS Code and Neovim support for PyPlyne files.
---

# Editor Support

PyPlyne has editor support for VS Code and Neovim. VS Code support currently
uses a source-checkout install path; track packaged VS Code installation in
[issue #4](https://github.com/pyplyne-org/pyplyne/issues/4). Neovim support
lives in [`pyplyne-org/pyplyne.nvim`](https://github.com/pyplyne-org/pyplyne.nvim)
and can be installed directly with Lazy.nvim or LazyVim.

Install PyPlyne in the project where you write `.pyplyne` files first. The
editor integrations start or connect to `pyplyne serve`, so the PyPlyne CLI must
be available from the editor workspace.

## VS Code

The local VS Code extension provides:

- TextMate syntax highlighting for `.pyplyne` files.
- Command palette and context-menu actions for running source.
- Default keybindings for line, selection, block, file, and assignment runs.
- Diagnostics in the Problems view when a session response includes a source
  location. Locations are reliable for full-file runs; for selections, current
  blocks, and current lines, reported lines are relative to the sent snippet.

### Install From This Repository

This is a development/source-checkout install path. VS Code does not install an
extension directly from a GitHub subdirectory the way Python package managers
can install PyPlyne from Git. For a normal user install path, track
[issue #4](https://github.com/pyplyne-org/pyplyne/issues/4).

From a source checkout:

```bash
mkdir -p ~/.vscode/extensions
rm -f ~/.vscode/extensions/pyplyne.pyplyne-0.1.1
ln -s "/path/to/pyplyne/editors/vscode-pyplyne" ~/.vscode/extensions/pyplyne.pyplyne-0.1.1
```

On Windows, copy or junction the extension folder into your VS Code extensions
directory, for example:

```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.vscode\extensions
New-Item -ItemType Junction `
  -Path $env:USERPROFILE\.vscode\extensions\pyplyne.pyplyne-0.1.1 `
  -Target C:\path\to\pyplyne\editors\vscode-pyplyne
```

Reload VS Code, open your Python project, then open a `.pyplyne` file. If the
file is not detected as PyPlyne, use the language picker in the status bar and
choose `PyPlyne`.

By default, the extension starts PyPlyne with:

```text
uv run pyplyne serve --host 127.0.0.1 --port 8765
```

If your project uses `pip` and `pyplyne` is available directly on `PATH`, set:

```json
{
  "pyplyne.executable": "pyplyne",
  "pyplyne.executableArgs": []
}
```

### First Run

1. Open a `.pyplyne` file.
2. Put the cursor on a line, select a few lines, or place it inside a
   blank-line-separated block.
3. Press `Cmd+Enter` on macOS or `Ctrl+Enter` on Windows/Linux.

The extension starts `pyplyne serve` automatically if no compatible session is
already running.

Default keybindings:

| Keybinding | Action |
| --- | --- |
| `Cmd+Enter` / `Ctrl+Enter` | Run selection or current line. |
| `Cmd+Shift+Enter` / `Ctrl+Shift+Enter` | Run current block. |
| `Cmd+Option+Shift+Enter` / `Ctrl+Alt+Shift+Enter` | Run current assignment and show the assigned value. |
| `Cmd+Shift+Down` / `Ctrl+Shift+Down` | Go to next block. |
| `Cmd+Shift+Up` / `Ctrl+Shift+Up` | Go to previous block. |

## Neovim

The Neovim plugin registers the `pyplyne` filetype, wires the Tree-sitter
grammar into `nvim-treesitter`, provides highlight/indent queries, and adds
interactive commands backed by `pyplyne serve`.

Requirements:

- Neovim 0.10+
- `nvim-treesitter`
- `node`/`npm`, because the local parser is generated from `grammar.js`
- a C compiler available on `PATH`
- `curl`, used by session health and shape checks
- the PyPlyne CLI available from the Neovim working directory

### Install With LazyVim

Create `~/.config/nvim/lua/plugins/pyplyne.lua`:

```lua
return {
  {
    "pyplyne-org/pyplyne.nvim",
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

By default, the plugin runs `uv run pyplyne`. If `pyplyne` is installed directly
on `PATH`, configure:

```lua
opts = {
  executable = "pyplyne",
  executable_args = {},
}
```

Default buffer-local keymaps:

| Keymap | Action |
| --- | --- |
| `<leader>pl` | Run current line. |
| `<leader>pr` | Run visual selection. |
| `<leader>pb` | Run current block. |
| `<leader>pa` | Run current assignment and show the assigned value. |
| `<leader>pf` | Run current file. |
| `<leader>ps` | Show session shapes. |
| `<leader>pS` | Start session. |
| `<leader>px` | Stop session. |

Terminal Neovim cannot reliably receive every `Ctrl+Enter` or
`Ctrl+Shift+Enter` combination across terminals, so the plugin uses leader
mappings by default. Override them through `opts.keymaps`.

Useful options:

| Option | Default | Purpose |
| --- | --- | --- |
| `executable` | `"uv"` | Program used to start PyPlyne. |
| `executable_args` | `{ "run", "pyplyne" }` | Arguments before the PyPlyne subcommand. |
| `host` | `"127.0.0.1"` | Session host. |
| `port` | `8765` | Session port. |
| `startup_timeout_ms` | `30000` | Time to wait for a started server. |
| `request_timeout_ms` | `30000` | Time to wait for snippet responses. |
| `auto_start_server` | `true` | Start a server automatically before commands. |
| `register_treesitter` | `true` | Register the local parser with nvim-treesitter. |
| `parser_url` | `nil` | Override the parser source path or URL. |

### Parser Only

If you only want Tree-sitter registration without the interactive commands, add
a parser entry to your Neovim config:

```lua
local parser_config = require("nvim-treesitter.parsers").get_parser_configs()

parser_config.pyplyne = {
  install_info = {
    url = "https://github.com/pyplyne-org/pyplyne.nvim",
    files = { "src/parser.c" },
    location = "tree-sitter-pyplyne",
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

## Web Syntax Highlighting

For documentation sites and web apps that use Prism, use the standalone
`prism-pyplyne` package. See `packages/prism-pyplyne/README.md` in this
repository for install and Docusaurus setup.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Commands do not appear. | Confirm the file uses `.pyplyne`, then set the language mode to `PyPlyne` and reload the editor. |
| The session fails to start. | Confirm the configured command works from the project root, for example `uv run pyplyne run --help` or `pyplyne run --help`. |
| `uv` cannot be found. | Install `uv`, open the editor from a shell with `uv` on `PATH`, or configure the editor to run `pyplyne` directly. |
| Port `8765` is already in use. | Stop the other process or change the editor's configured PyPlyne port. |
| Results use stale variables. | Restart the session or run the full file to rebuild state from top to bottom. |

Editor stop commands only stop a server process started by that editor
instance. They do not stop an unrelated `pyplyne serve` process already running
on the same port.
