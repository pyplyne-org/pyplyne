from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_homepage_demo_code_keeps_real_newlines_and_avoids_prism_rehighlight():
    source = (PROJECT_ROOT / "site" / "src" / "pages" / "index.jsx").read_text(
        encoding="utf-8"
    )
    demo_code_start = source.index("function DemoCode")
    demo_code_end = source.index("function MiniTable")
    demo_code_source = source[demo_code_start:demo_code_end]

    assert '<code className="language-pyplyne">' not in demo_code_source
    assert "styles.codeLineBreak" in demo_code_source
    assert r"{'\n'}" in demo_code_source
