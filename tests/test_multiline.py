"""
Tests for multi-line ("long") calc rendering, toggled by the ``-m``/``--multiline``
comment command (standalone to affect every following line, or trailing to affect a
single line). A long calc breaks the one-liner into rows aligned on ``=``:
``target = symbolic`` first, then ``= numeric`` and ``= result`` on their own rows,
with any trailing comment riding the last (result) row.
"""
import pytest

from handcalcs.parsing.sequence import HcSequence
from handcalcs.renderers.plaintext import PlainTextRenderer
from handcalcs.renderers.html import HTMLRenderer


def _render_plain(source, names):
    r = PlainTextRenderer()
    ctx = r.create_context()
    tree = r.render(HcSequence.from_source(source, names, {}), ctx)
    return r.join(tree, ctx)


def _render_html(source, names):
    r = HTMLRenderer()
    ctx = r.create_context()
    tree = r.render(HcSequence.from_source(source, names, {}), ctx)
    return r.complete(tree, ctx)


def test_plaintext_global_multiline_aligns_on_equals():
    # A standalone `# hc: -m` puts every following (non-param) calc into long mode;
    # the numeric and result rows align under the first row's '='.
    out = _render_plain(
        "# hc: -m\na = 5\nb = 3\nd = a * b + a\n",
        {"a": 5, "b": 3, "d": 20},
    )
    assert out == (
        "a = 5\n"
        "b = 3\n"
        "d = a * b + a\n"
        "  = 5 * 3 + 5\n"
        "  = 20\n"
    )


def test_plaintext_inline_multiline_affects_only_its_line():
    # A trailing `# hc: -m` only breaks its own line; the sibling stays a one-liner.
    out = _render_plain(
        "a = 5\nb = 3\nd = a * b + a  # hc: -m\ne = a + b\n",
        {"a": 5, "b": 3, "d": 20, "e": 8},
    )
    assert out == (
        "a = 5\n"
        "b = 3\n"
        "d = a * b + a\n"
        "  = 5 * 3 + 5\n"
        "  = 20\n"
        "e = a + b = 5 + 3 = 8\n"
    )


def test_plaintext_comment_rides_result_row():
    # A regular trailing comment lands on the last (result) row, not the first.
    out = _render_plain(
        "# hc: -m\na = 5\nb = 3\nd = a * b + a  # the answer\n",
        {"a": 5, "b": 3, "d": 20},
    )
    assert out.splitlines()[-1] == "  = 20 (the answer)"


def test_plaintext_param_line_stays_one_liner_under_multiline():
    # A bare value assignment is a param line and is never expanded, even in -m mode.
    out = _render_plain("# hc: -m\na = 5\n", {"a": 5})
    assert out == "a = 5\n"


def test_html_multiline_emits_left_aligned_table():
    # The HTML renderer reuses the params table (id/eq/val <td>s) with an extra
    # `hc-multiline` class (left-aligned); each row is one id/eq/val triple.
    out = _render_html("# hc: -m\na = 5\nb = 3\nd = a * b + a\n", {"a": 5, "b": 3, "d": 20})
    assert '<table class="hc-params hc-multiline">' in out
    # Target only on the first row; empty id cells thereafter so '=' aligns.
    assert out.count("<tr>") == 3
    assert '<td class="hc-param-id">d</td>' in out
    assert '<td class="hc-param-id"></td>' in out
    # The left-aligned override is present in the stylesheet.
    assert "table.hc-multiline){align-self:start;}" in out


def test_html_params_table_is_content_sized_and_centered():
    # The params table no longer stretches to the full flex width (which made the
    # '=' look over-padded): it is content-sized and centered.
    out = _render_html("f = 1; g = 2; h = 4\n", {"f": 1, "g": 2, "h": 4})
    assert "width:auto;align-self:center;" in out
