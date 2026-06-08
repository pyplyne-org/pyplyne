import importlib.util
from pathlib import Path

import pytest

import pyplyne
from pyplyne import PyPlyneSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "site" / "scripts" / "generate_python_api_reference.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_python_api_reference", GENERATOR_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_api_reference_discovers_public_session_methods():
    generator = _load_generator_module()

    expected = [
        name
        for name, value in vars(PyPlyneSession).items()
        if callable(value) and not name.startswith("_")
    ]

    assert generator.public_methods(PyPlyneSession) == expected
    assert {"run", "load_file", "get", "get_df", "get_seq"}.issubset(expected)


def test_python_api_reference_uses_package_public_exports():
    generator = _load_generator_module()

    assert [name for name, _ in generator.public_exports()] == list(pyplyne.__all__)
    assert {"run", "run_file", "PyPlyneSession"}.issubset(pyplyne.__all__)


def test_python_api_reference_summarizes_public_api_from_docstrings():
    generator = _load_generator_module()

    assert not hasattr(generator, "PUBLIC_API_DESCRIPTIONS")
    assert (
        generator.docstring_summary(pyplyne.run)
        == "Run PyPlyne source once without managing a persistent session."
    )

    table = generator.public_surface_table(generator.public_exports())

    assert (
        "| `run` | Run PyPlyne source once without managing a persistent session. |"
        in table
    )
    assert (
        "| `run_file` | Run a `.pyplyne` file once without managing a persistent session. |"
        in table
    )


def test_python_api_reference_summary_uses_first_docstring_line():
    generator = _load_generator_module()

    class Example:
        """First line summary.

        Extra detail should not appear in the public surface table.
        """

    assert generator.docstring_summary(Example) == "First line summary."


def test_python_api_reference_requires_public_docstrings():
    generator = _load_generator_module()

    def undocumented():
        pass

    with pytest.raises(ValueError, match="missing a docstring"):
        generator.docstring_summary(undocumented)
