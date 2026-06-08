import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

NVIM_ROOT = Path(__file__).resolve().parents[1] / "editors" / "nvim-pyplyne"
GRAMMAR_ROOT = NVIM_ROOT / "tree-sitter-pyplyne"


def run_nvim_lua(source: str):
    if not shutil.which("nvim"):
        pytest.skip("nvim is not installed")

    result = subprocess.run(
        [
            "nvim",
            "--headless",
            "-u",
            "NONE",
            "-c",
            f"set rtp+={NVIM_ROOT}",
            "-c",
            "lua " + textwrap.dedent(source),
            "-c",
            "qa",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_neovim_treesitter_files_exist():
    assert (NVIM_ROOT / "README.md").exists()
    assert (NVIM_ROOT / "plugin" / "pyplyne.lua").exists()
    assert (NVIM_ROOT / "lua" / "pyplyne" / "init.lua").exists()
    assert (NVIM_ROOT / "queries" / "pyplyne" / "highlights.scm").exists()
    assert (NVIM_ROOT / "queries" / "pyplyne" / "indents.scm").exists()
    assert (GRAMMAR_ROOT / "grammar.js").exists()
    assert (GRAMMAR_ROOT / "queries" / "highlights.scm").exists()
    assert (GRAMMAR_ROOT / "queries" / "indents.scm").exists()
    assert (GRAMMAR_ROOT / "test" / "corpus" / "basic.txt").exists()
    assert (GRAMMAR_ROOT / "tree-sitter.json").exists()


def test_neovim_treesitter_package_metadata():
    package = json.loads((GRAMMAR_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "tree-sitter-pyplyne"
    assert package["tree-sitter"][0]["scope"] == "source.pyplyne"
    assert package["tree-sitter"][0]["file-types"] == ["pyplyne"]
    assert package["scripts"]["generate"] == "tree-sitter generate"
    assert package["scripts"]["test"] == "tree-sitter test"

    config = json.loads((GRAMMAR_ROOT / "tree-sitter.json").read_text(encoding="utf-8"))
    grammar = config["grammars"][0]
    assert grammar["name"] == "pyplyne"
    assert grammar["scope"] == "source.pyplyne"
    assert grammar["file-types"] == ["pyplyne"]


def test_neovim_treesitter_readme_documents_installation():
    readme = (NVIM_ROOT / "README.md").read_text(encoding="utf-8")

    assert "pyplyne.nvim" in readme
    assert 'dir = "/path/to/pyplyne/editors/nvim-pyplyne"' in readme
    assert 'require("pyplyne").setup(opts)' in readme
    assert "lazy = false" in readme
    assert "parser_config.pyplyne" in readme
    assert "vim.filetype.add" in readme
    assert ":TSInstall pyplyne" in readme
    assert "LazyVim" in readme
    assert "Mason does not install Tree-sitter parsers" in readme
    assert "Terminal Neovim cannot reliably receive every `Ctrl+Enter`" in readme


def test_neovim_plugin_exposes_commands_and_keymaps():
    plugin = (NVIM_ROOT / "lua" / "pyplyne" / "init.lua").read_text(encoding="utf-8")

    for command in [
        "PyplyneStart",
        "PyplyneStop",
        "PyplyneRunLine",
        "PyplyneRunSelection",
        "PyplyneRunBlock",
        "PyplyneRunAssignment",
        "PyplyneRunFile",
        "PyplyneShapes",
    ]:
        assert command in plugin

    for keymap in [
        'run_line = "<leader>pl"',
        'run_selection = "<leader>pr"',
        'run_block = "<leader>pb"',
        'run_assignment = "<leader>pa"',
        'run_file = "<leader>pf"',
        'show_shapes = "<leader>ps"',
        'start_session = "<leader>pS"',
        'stop_session = "<leader>px"',
    ]:
        assert keymap in plugin


def test_neovim_plugin_default_keymaps_are_buffer_local_callbacks():
    run_nvim_lua(
        """
        vim.cmd("filetype on")
        vim.g.mapleader = " "
        local pyplyne = require("pyplyne")
        pyplyne.setup({ keymaps = { enable = true } })
        vim.cmd("edit /tmp/pyplyne-keymap-check.pyplyne")

        local function has(mode, lhs, desc)
          for _, map in ipairs(vim.api.nvim_buf_get_keymap(0, mode)) do
            if map.lhs == lhs and map.desc == desc and type(map.callback) == "function" then
              return true
            end
          end
          return false
        end

        assert(has("n", " pl", "PyPlyne run current line"))
        assert(has("n", " pb", "PyPlyne run current block"))
        assert(has("n", " pa", "PyPlyne run assignment and show result"))
        assert(has("n", " pf", "PyPlyne run file"))
        assert(has("n", " ps", "PyPlyne show shapes"))
        assert(has("n", " pS", "PyPlyne start session"))
        assert(has("n", " px", "PyPlyne stop session"))
        assert(has("v", " pr", "PyPlyne run selection"))
        """
    )


def test_neovim_plugin_keymap_invokes_lua_callback():
    run_nvim_lua(
        """
        vim.cmd("filetype on")
        vim.g.mapleader = " "
        local pyplyne = require("pyplyne")
        pyplyne.setup({ keymaps = { enable = true } })
        pyplyne.run_line = function()
          vim.g.pyplyne_run_line_called = 1
        end

        vim.cmd("edit /tmp/pyplyne-keymap-invoke-check.pyplyne")
        vim.api.nvim_feedkeys(" pl", "x", false)
        vim.cmd("redraw")
        assert(vim.g.pyplyne_run_line_called == 1, vim.inspect(vim.g.pyplyne_run_line_called))
        """
    )


def test_neovim_plugin_reports_missing_executable_before_starting_session():
    run_nvim_lua(
        """
        local messages = {}
        vim.notify = function(message, level, opts)
          table.insert(messages, { message = message, level = level, title = opts and opts.title })
        end

        local pyplyne = require("pyplyne")
        pyplyne.setup({
          executable = "definitely-missing-pyplyne-executable",
          executable_args = {},
          port = 18765,
          startup_timeout_ms = 50,
          keymaps = { enable = false },
        })

        assert(pyplyne.start_session() == false)
        assert(#messages == 1, vim.inspect(messages))
        assert(messages[1].title == "PyPlyne", vim.inspect(messages))
        assert(messages[1].level == vim.log.levels.ERROR, vim.inspect(messages))
        assert(
          messages[1].message:match("executable `definitely%-missing%-pyplyne%-executable` was not found on PATH"),
          messages[1].message
        )
        assert(messages[1].message:match("default executable is uv"), messages[1].message)
        """
    )


def test_neovim_treesitter_highlights_cover_core_language():
    highlights = (GRAMMAR_ROOT / "queries" / "highlights.scm").read_text(
        encoding="utf-8"
    )

    for token in [
        "pipe_operator",
        "(shape)",
        "where",
        "map",
        "filter",
        "group_by",
        "summarize",
    ]:
        assert token in highlights
