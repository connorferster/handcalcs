"""
Tests for the HTMLRenderer's theme and styling hooks: theme colours, import
chips, block-header callouts and comparison spacing.
"""

import pytest

from tests.html_markup import var, without_var

from handcalcs.parsing.sequence import HcSequence
from handcalcs.renderers.html import (
    DEFAULT_THEME,
    HTMLRenderer,
    stretch_brackets,
    theme_variables,
)


def _render_markup(source, names, **kwargs):
    r = HTMLRenderer(**kwargs)
    ctx = r.create_context()
    tree = r.render(HcSequence.from_source(source, names, {}), ctx)
    return r.complete(tree, ctx)


def _render(source, names, **kwargs):
    """The render without its ``<var>`` tags: most tests here are about other
    markup (see ``test_names_are_italic_vars`` for those)."""
    return without_var(_render_markup(source, names, **kwargs))


def test_default_theme_derives_the_petrol_palette():
    # The accent is the theme itself; the guides keep its hue, then turn it by
    # +210 and +40 degrees.
    theme = theme_variables(DEFAULT_THEME)
    assert theme["--hc-accent"] == "#0B5F66"
    assert (theme["--hc-guide-1"], theme["--hc-guide-2"], theme["--hc-guide-3"]) == (
        "#85B8BD",
        "#D5B386",
        "#A8B0C7",
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
    assert (
        '<div class="hc-header"><span class="hc-kw">Since</span> (a &gt; 2) → (3 &gt; 2)'
        in out
    )
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
    return without_var(r.complete(tree, ctx))


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
        "y = np.sqrt(x) + np.hypot(x, x)\nz = np.pi\n",
        {"np": np, "x": 4, "y": 0, "z": 0},
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


# --- stacked fractions and powers ---


def frac(num: str, den: str, sep: str = "/") -> str:
    return (
        f'<span class="hc-frac"><span class="hc-num">{num}</span>'
        f'<span class="hc-hidden">{sep}</span><span class="hc-den">{den}</span></span>'
    )


def hidden(text: str) -> str:
    return f'<span class="hc-hidden">{text}</span>'


def body(out: str) -> str:
    return out.split("</style>", 1)[1]


def test_division_is_a_stacked_fraction():
    out = _render("a = 1\nb = 2\nc = a / b\n", {"a": 1, "b": 2, "c": 0.5})
    assert f"c = {frac('a', 'b')} = {frac('1', '2')} =" in out


def test_fraction_keeps_its_brackets_hidden():
    names = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 0.0}
    out = _render("e = (a + b) / (c * d)\n", names)
    group = hidden("(") + "{}" + hidden(")")
    assert frac(group.format("a + b"), group.format("c · d")) in out


def test_nested_fractions():
    names = {"a": 1, "b": 2, "c": 3, "z": 0.0}
    out = _render("z = (a / b + 1) / (c / (a + b))\n", names)
    group = hidden("(") + "{}" + hidden(")")
    numerator = group.format(frac("a", "b") + " + 1")
    denominator = group.format(frac("c", group.format("a + b")))
    assert f"z = {frac(numerator, denominator)} =" in out


def test_fraction_in_an_exponent_stays_inline():
    names = {"a": 2, "b": 3, "c": 4, "x": 0.0}
    out = body(_render("x = a**(1/2) + a**(b/c) + a**b\n", names))
    assert "x = a<sup>1/2</sup> + a<sup>b/c</sup> + a<sup>b</sup> =" in out
    assert "**" not in out and "hc-frac" not in out


def test_fraction_with_a_fractional_exponent():
    names = {"a": 2, "b": 3, "x": 0.0}
    out = _render("x = a**(1/3) / b\n", names)
    assert frac("a<sup>1/3</sup>", "b") in out


def test_power_base_is_bracketed():
    names = {"a": 2, "b": 3, "c": -4, "x": 0.0}
    out = _render("x = (a + b)**2 + c**2 + (a**b)**2\n", names)
    assert (
        "x = (a + b)<sup>2</sup> + c<sup>2</sup> + (a<sup>b</sup>)<sup>2</sup>" in out
    )
    assert "(-4)<sup>2</sup>" in out


def test_floor_division_is_a_fraction_in_floor_brackets():
    out = _render("c = 7 // 2\n", {"c": 3})
    assert f"⌊{frac('7', '2', '//')}⌋" in out


def test_inline_fractions():
    names = {"a": 1, "b": 2, "c": 0.5}
    out = body(_render("c = (a + b) / a // b\n", names, fractions="inline"))
    assert "c = (a + b) / a // b =" in out and "hc-frac" not in out


def test_invalid_fractions_option():
    with pytest.raises(ValueError, match="'stacked', 'inline'"):
        HTMLRenderer(fractions="diagonal")


def test_brackets_around_a_fraction_stretch():
    names = {"a": 2, "b": 3, "x": 0.0}
    out = body(_render("x = (a / b)**2 + (a + b)**2\n", names))
    paren = '<span class="hc-paren hc-paren-1">{}</span>'
    assert (
        f"x = {paren.format('(')}{frac('a', 'b')}{paren.format(')')}<sup>2</sup>" in out
    )
    assert " + (a + b)<sup>2</sup>" in out


def test_brackets_around_nested_fractions_stretch_more():
    out = stretch_brackets("(" + frac(frac("a", "b"), "c") + ")")
    assert out.startswith('<span class="hc-paren hc-paren-2">(</span>')


def test_hidden_and_unpaired_brackets_are_left_alone():
    group = hidden("(") + frac("a", "b") + hidden(")")
    assert stretch_brackets(group) == group
    assert (
        stretch_brackets(") " + frac("a", "b") + " (") == ") " + frac("a", "b") + " ("
    )


def test_condition_header_brackets_stretch():
    out = _render("a = 3\nif a / 2 > 1:\n    b = 1\n", {"a": 3, "b": 1})
    assert '<span class="hc-paren hc-paren-1">(</span>' in out


# --- names in <var>, and the maths style ---


def test_names_are_italic_vars():
    names = {"w_f": 2.0, "L": 3.0, "M_f": 0.0}
    out = _render_markup("M_f = w_f * L**2\n", names)
    assert (
        f"{var('M<sub>f</sub>')} = {var('w<sub>f</sub>')} · {var('L')}<sup>2</sup>"
        in out
    )


def test_function_and_module_names_are_upright():
    import math

    r = HTMLRenderer()
    global_ns = {"math": math, "x": 1.0, "y": 0.0}
    ctx = r.create_context(global_ns=global_ns)
    tree = r.render(
        HcSequence.from_source("y = math.sin(x) + math.hypot(x, x)\n", global_ns, {}),
        ctx,
    )
    out = r.complete(tree, ctx)
    assert "sin(<var>x</var>) + hypot(<var>x</var>, <var>x</var>)" in out


def test_maths_style_is_in_the_stylesheet():
    out = _render_markup("a = 1\n", {"a": 1})
    assert '--hc-math-font:"Cambria Math",Cambria,"STIX Two Text","DejaVu Serif"' in out
    assert "--hc-highlight:rgba(11,95,102,0.12);" in out
    assert ".handcalcs :where(var){font-style:italic;" in out


# --- colours WeasyPrint can draw ---


def test_no_color_mix_in_the_stylesheet():
    # WeasyPrint drops color-mix() declarations, so tints are plain rgba().
    out = _render("a = 1\nif a > 0:\n    b = 2\n", {"a": 1, "b": 2})
    assert "color-mix" not in out
    assert "--hc-tint:rgba(11,95,102,0.09);" in out
    assert "--hc-tint:rgba(11,95,102,0.3);" in out  # on a dark host


def test_result_highlight_follows_the_theme():
    out = _render("a = 1\n", {"a": 1}, theme_color="#7C3AED")
    assert "--hc-highlight:rgba(124,58,237,0.12);" in out


def test_line_break_is_a_spacer_div():
    # `# hc: -b` adds a spacer between the two lines (it used to add nothing).
    out = _render_markup("a = 1\n# hc: -b\nb = 2\n", {"a": 1, "b": 2})
    assert out.count('<div class="hc-break"></div>') == 1
    assert out.index("hc-break") < out.index(">b<")


def test_line_break_has_a_height():
    out = _render("a = 1\n", {"a": 1})
    assert ".handcalcs :where(.hc-break){height:1em;}" in out
