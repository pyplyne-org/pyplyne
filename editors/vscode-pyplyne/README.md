# PyPlyne VS Code Extension

VS Code support for `.pyplyne` files.

This extension is currently installed from this repository. Marketplace
publishing is pending.

It provides syntax highlighting, editor commands, default keybindings,
diagnostics, and a lightweight interactive execution loop backed by
`pyplyne serve`.

## Install From This Repository

Install PyPlyne in the project where you write `.pyplyne` files first. The
extension starts sessions with `uv run pyplyne` by default.

From a source checkout of this repository, symlink the extension into VS Code:

```bash
mkdir -p ~/.vscode/extensions
rm -f ~/.vscode/extensions/pyplyne.pyplyne-0.1.1
ln -s "/path/to/pyplyne/editors/vscode-pyplyne" ~/.vscode/extensions/pyplyne.pyplyne-0.1.1
```

Reload VS Code, open your Python project, then open a `.pyplyne` file. If the
file is not detected as PyPlyne, use the language picker in the status bar and
choose `PyPlyne`.

For extension development, open this folder in VS Code and press `F5` to launch
an Extension Development Host.

## Settings

By default, the extension starts PyPlyne with:

```text
uv run pyplyne serve --host 127.0.0.1 --port 8765
```

If `pyplyne` is installed directly on your `PATH`, set:

```json
{
  "pyplyne.executable": "pyplyne",
  "pyplyne.executableArgs": []
}
```

You can also change the session endpoint:

```json
{
  "pyplyne.host": "127.0.0.1",
  "pyplyne.port": 8765,
  "pyplyne.startupTimeoutMs": 30000
}
```

## Commands

Open a `.pyplyne` file and use the command palette:

```text
PyPlyne: Start Session
PyPlyne: Stop Session
PyPlyne: Run Selection
PyPlyne: Run Current Line
PyPlyne: Run Current Block
PyPlyne: Run Current Assignment and Show Result
PyPlyne: Run Current File
PyPlyne: Go to Next Block
PyPlyne: Go to Previous Block
PyPlyne: Show Session Shapes
```

Default keybindings:

| Keybinding | Action |
| --- | --- |
| `Cmd+Enter` / `Ctrl+Enter` | Run selection or current line. |
| `Cmd+Shift+Enter` / `Ctrl+Shift+Enter` | Run current block. |
| `Cmd+Option+Shift+Enter` / `Ctrl+Alt+Shift+Enter` | Run current assignment and show the assigned value. |
| `Cmd+Shift+Down` / `Ctrl+Shift+Down` | Go to next block. |
| `Cmd+Shift+Up` / `Ctrl+Shift+Up` | Go to previous block. |

Results appear in the `PyPlyne` output panel. Errors use the same readable
diagnostics as `pyplyne send`, and the extension publishes the error location to
VS Code's Problems view when the session response includes a source line.
