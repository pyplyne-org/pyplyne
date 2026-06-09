from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_editor_docs_reference_external_neovim_plugin_repo():
    editor_docs = (PROJECT_ROOT / "docs" / "editor.md").read_text(encoding="utf-8")

    assert "pyplyne-org/pyplyne.nvim" in editor_docs
    assert '    "pyplyne-org/pyplyne.nvim",' in editor_docs
    assert "https://github.com/pyplyne-org/pyplyne.nvim" in editor_docs
    assert "editors/nvim-pyplyne" not in editor_docs
    assert "issue #5" not in editor_docs
