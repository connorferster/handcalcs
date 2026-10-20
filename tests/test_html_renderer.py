"""
Tests for the HTMLRenderer's theme and styling hooks: theme colours, import
chips, block-header callouts and comparison spacing.
"""
import pytest

from handcalcs.parsing.sequence import HcSequence
from handcalcs.renderers.html import HTMLRenderer, theme_variables, DEFAULT_THEME


def _render(source, names, **kwargs):
    r = HTMLRenderer(**kwargs)
    ctx = r.create_context()
    tree = r.render(HcSequence.from_source(source, names, {}), ctx)
    return r.complete(tree, ctx)


def test_default_theme_derives_the_petrol_palette():
    # The accent is the theme itself; the guides keep its hue, then turn it by
    # +210 and +40 degrees.
    theme = theme_variables(DEFAULT_THEME)
    assert theme["--hc-accent"] == "#0B5F66"
    assert (theme["--hc-guide-1"], theme["--hc-guide-2"], theme["--hc-guide-3"]) == (
        "#85B8BD", "#D5B386", "#A8B0C7",
    )


def test_theme_color_sets_the_accent_variable():
    out = _render("a = 1\n", {"a": 1}, theme_color="#7a3b12")
    assert "--hc-accent:#7A3B12;" in out


def test_invalid_theme_color_raises():
    with pytest.raises(ValueError):
        HTMLRenderer(theme_color="teal")


def test_dark_hosts_get_a_lighter_accent():
    out = _render("a = 1\n", {"a": 1})
    assert '[data-jp-theme-light="false"]' in out
    assert "--hc-accent-text:var(--hc-accent-dark);" in out


def test_import_renders_as_chip():
    out = _render("from math import sqrt, pi\n", {})
    assert '<div class="hc-import">from math import sqrt, pi</div>' in out
    assert "[Python import]" not in out


def test_block_headers_mark_keywords_and_arrow():
    out = _render("a = 3\nif a > 2:\n    b = 1\n", {"a": 3, "b": 1})
    assert '<div class="hc-header"><span class="hc-kw">Since</span> (a &gt; 2) → (3 &gt; 2)' in out
    assert '<span class="hc-kw">is True:</span>' in out


def test_else_header_is_a_keyword():
    out = _render("a = 1\nif a > 2:\n    b = 1\nelse:\n    b = 2\n", {"a": 1, "b": 2})
    assert '<span class="hc-kw">Otherwise:</span>' in out


def test_comparisons_are_spaced_and_not_equal_is_a_sign():
    out = _render("a = 1\nc = a != 2\n", {"a": 1, "c": True})
    assert "a ≠ 2" in out


def test_prose_backticks_become_code():
    out = _render("# Use `and` here\na = 1\n", {"a": 1})
    assert "Use <code>and</code> here" in out


def _render_with_globals(source, global_ns):
    r = HTMLRenderer()
    ctx = r.create_context(global_ns=global_ns)
    tree = r.render(HcSequence.from_source(source, global_ns, {}), ctx)
    return r.complete(tree, ctx)


def test_math_prefix_is_dropped_from_function_calls():
    import math
    out = _render_with_globals(
        "y = math.sqrt(x) + math.sin(x)\n", {"math": math, "x": 4, "y": 0}
    )
    assert "y = √(x) + sin(x) = √(4) + sin(4)" in out
    assert "math." not in out


def test_aliased_math_module_is_recognised():
    import math
    out = _render_with_globals("y = m.sqrt(x)\n", {"m": math, "x": 4, "y": 2})
    assert "y = √(x) = √(4)" in out


def test_math_constants_show_as_symbols():
    import math
    out = _render_with_globals(
        "y = math.pi * math.e\nz = math.inf\n", {"math": math, "y": 0, "z": 0}
    )
    assert "y = π · e = 3.1416 · 2.7183" in out
    # The substituted value (∞) repeats the symbol, so that column is dropped.
    assert 'z = ∞ = <span class="hc-result">0</span>' in out


def test_numpy_prefix_is_dropped_only_for_maths_functions():
    import math, types
    np = types.ModuleType("numpy")
    np.sqrt, np.hypot, np.pi = math.sqrt, math.hypot, math.pi
    out = _render_with_globals(
        "y = np.sqrt(x) + np.hypot(x, x)\nz = np.pi\n", {"np": np, "x": 4, "y": 0, "z": 0}
    )
    assert "y = √(x) + hypot(x, x)" in out
    assert "z = π" in out
    # An array function keeps its prefix.
    np.linspace = lambda *a: [0]
    out = _render_with_globals("w = np.linspace(0, 1)\n", {"np": np, "w": [0]})
    assert "np.linspace(0, 1)" in out


def test_other_namespaces_keep_their_prefix():
    class Beam:
        e = 3
    out = _render_with_globals("w = beam.e * 2\n", {"beam": Beam(), "w": 6})
    assert "beam.e" in out
