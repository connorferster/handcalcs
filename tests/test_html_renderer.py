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


def test_default_theme_matches_reportlab_palette():
    # Same derivation as the ReportLab renderer's Palette.from_theme (petrol).
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
