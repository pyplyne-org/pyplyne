import json
from pathlib import Path

EXTENSION_ROOT = Path(__file__).resolve().parents[1] / "editors" / "vscode-pyplyne"


def test_vscode_extension_manifest_paths_exist():
    manifest = json.loads((EXTENSION_ROOT / "package.json").read_text(encoding="utf-8"))

    assert (EXTENSION_ROOT / manifest["main"]).exists()

    for language in manifest["contributes"]["languages"]:
        assert (EXTENSION_ROOT / language["configuration"]).exists()

    for grammar in manifest["contributes"]["grammars"]:
        assert (EXTENSION_ROOT / grammar["path"]).exists()


def test_vscode_textmate_grammar_is_valid_json():
    grammar_path = EXTENSION_ROOT / "syntaxes" / "pyplyne.tmLanguage.json"
    grammar = json.loads(grammar_path.read_text(encoding="utf-8"))

    assert grammar["scopeName"] == "source.pyplyne"
    assert grammar["patterns"]
    assert "repository" in grammar


def test_vscode_extension_contributes_interactive_commands():
    manifest = json.loads((EXTENSION_ROOT / "package.json").read_text(encoding="utf-8"))
    commands = {command["command"] for command in manifest["contributes"]["commands"]}

    assert {
        "pyplyne.startSession",
        "pyplyne.stopSession",
        "pyplyne.runSelection",
        "pyplyne.runCurrentLine",
        "pyplyne.runCurrentBlock",
        "pyplyne.runCurrentAssignmentAndShowResult",
        "pyplyne.runFile",
        "pyplyne.goToNextBlock",
        "pyplyne.goToPreviousBlock",
        "pyplyne.showShapes",
    }.issubset(commands)
    assert "onLanguage:pyplyne" in manifest["activationEvents"]

    keybindings = {
        binding["command"]: binding
        for binding in manifest["contributes"]["keybindings"]
    }
    assert keybindings["pyplyne.runCurrentLine"]["mac"] == "cmd+enter"
    assert keybindings["pyplyne.runCurrentBlock"]["mac"] == "cmd+shift+enter"
    assert (
        keybindings["pyplyne.runCurrentAssignmentAndShowResult"]["mac"]
        == "cmd+alt+shift+enter"
    )
    assert keybindings["pyplyne.goToNextBlock"]["mac"] == "cmd+shift+down"
    assert keybindings["pyplyne.goToPreviousBlock"]["mac"] == "cmd+shift+up"
    assert (
        keybindings["pyplyne.goToNextBlock"]["when"]
        == "editorTextFocus && editorLangId == pyplyne"
    )
    palette_commands = {
        item["command"] for item in manifest["contributes"]["menus"]["commandPalette"]
    }
    assert "pyplyne.goToNextBlock" in palette_commands
    assert "pyplyne.goToPreviousBlock" in palette_commands


def test_vscode_extension_surfaces_process_launch_errors():
    extension = (EXTENSION_ROOT / "extension.js").read_text(encoding="utf-8")

    assert 'this.process.once("error"' in extension
    assert "Could not launch" in extension
    assert "Spawn PATH" in extension
    assert 'runCommand("start session"' in extension
    assert "vscode.window.showErrorMessage" in extension


def test_vscode_extension_labels_interactive_runs():
    extension = (EXTENSION_ROOT / "extension.js").read_text(encoding="utf-8")

    assert 'kind: "current block"' in extension
    assert 'kind: "current assignment + result"' in extension
    assert 'kind: "current line"' in extension
    assert 'kind: "selection"' in extension
    assert 'kind: "file"' in extension
    assert "sourcePreview(source)" in extension
    assert "(no output)" in extension
    assert "goToNextBlock" in extension
    assert "goToPreviousBlock" in extension
    assert "assignedNameFromBlock" in extension
