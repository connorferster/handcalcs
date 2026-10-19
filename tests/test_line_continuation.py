"""
Tests for line continuations (#259): a calc whose expression is continued over
several source lines (``\\`` or a break inside brackets) breaks at the same place in
the rendered output. The calc is laid out like a ``-m`` calc, with a continuation
row (no ``=``) for each continued segment of the symbolic and numeric columns.
"""
from handcalcs import HandCalcs
from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.plaintext import PlainTextRenderer


def _render(renderer, source):
    names = {}
    exec(source, names)
    return HandCalcs(renderer)(source, names)


def _expr(source):
    return AST_Parser()(source)[0].expression_tree[0]


def test_parser_records_break_after_operator():
    assert _expr("s = a + \\\n    b\n").line_break == "after"


def test_parser_records_break_before_operator():
    assert _expr("s = a \\\n    + b\n").line_break == "before"


def test_parser_records_bracketed_break():
    # The operator ends the line; the comment after it is ignored.
    node = _expr("s = (a +  # note\n    b) * c\n")
    assert node.line_break == ""
    assert node.left.line_break == "after"


def test_parser_no_break_on_one_line():
    assert _expr("s = a + b\n").line_break == ""


def test_plaintext_break_after_operator():
    out = _render(PlainTextRenderer(), "a = 2\nb = 3\nc = a * b + \\\n    b\n")
    assert out == (
        "a = 2\n"
        "b = 3\n"
        "c = a * b +\n"
        "      b\n"
        "  = 2 * 3 +\n"
        "      3\n"
        "  = 9\n"
    )


def test_plaintext_break_before_operator_and_comment_on_result_row():
    out = _render(PlainTextRenderer(), "a = 2\nb = 3\nc = a * b \\\n    - b  # net\n")
    assert out.splitlines()[2:] == [
        "c = a * b",
        "      - b",
        "  = 2 * 3",
        "      - 3",
        "  = 3 (net)",
    ]


def test_plaintext_several_breaks():
    out = _render(PlainTextRenderer(), "a = 2\nc = a + \\\n    a + \\\n    a\n")
    assert out.splitlines()[1:4] == ["c = a +", "      a +", "      a"]


def test_break_inside_brackets_or_fraction_is_ignored():
    # A break inside a bracketed group or a fraction cannot be kept, so the calc
    # renders as one line with normal spacing.
    source = "a = 2\nb = 3\nc = (a +\n    b) / b\nd = b * (a -\n    b)\n"
    plain = _render(PlainTextRenderer(), source)
    assert "c = (a + b) / b = (2 + 3) / 3" in plain
    assert "d = b * (a - b) = 3 * (2 - 3)" in plain
    latex = _render(LatexRenderer(), source)
    assert "\\frac{a + b}{b}" in latex


def test_latex_continuation_rows():
    out = _render(LatexRenderer(), "a = 2\nb = 3\nc = a / b + \\\n    b\n")
    assert (
        "c &= \\frac{a}{b} +{} \\\\\n"
        "& \\quad {}b \\\\\n"
        "&= \\frac{2}{3} +{} \\\\\n"
        "& \\quad {}3 \\\\\n"
        "&= 3.6667"
    ) in out


def test_html_continuation_rows():
    out = _render(HTMLRenderer(), "a = 2\nb = 3\nc = a * b + \\\n    b\n")
    assert '<table class="hc-params hc-multiline">' in out
    assert (
        '<td class="hc-param-eq"></td><td class="hc-param-val">&emsp;&emsp;b</td>'
        in out
    )
    assert '<span class="hc-result">9</span>' in out


def test_break_with_multiline_command():
    # -m on a continued calc gives the same grid.
    source = "a = 2\nb = 3\nc = a * b + \\\n    b\n"
    assert _render(PlainTextRenderer(), source) == _render(
        PlainTextRenderer(), "# hc: -m\n" + source
    )


def test_literal_expression_with_break():
    # The symbolic and numeric columns of a literal-only expression are the same,
    # so only one of them is shown (as on one line: ``c = 2 + 3 = 5``).
    out = _render(PlainTextRenderer(), "c = 2 + \\\n    3\n")
    assert out == "c = 2 +\n      3\n  = 5\n"


def test_bracketed_whole_expression_with_break_stays_param_line():
    # Brackets around the whole expression hide the substitution (#79), so there
    # is nothing to break.
    out = _render(PlainTextRenderer(), "a = 2\nc = (a +\n    3)\n")
    assert out == "a = 2\nc = 5\n"
