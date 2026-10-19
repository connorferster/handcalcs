"""
Number literals written in the source keep their source text; the format code
applies only to calculated values (substitutions, results, parameter values).
"""

from collections import deque

from handcalcs import HandCalcs, PlainTextRenderer
from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.parsing.nodes import Constant
from handcalcs.renderers import HTMLRenderer, LatexRenderer, MarkdownRenderer
from handcalcs.renderers.base import _reify


def find_constants(node) -> list:
    """Every Constant in ``node``'s tree, in source order."""
    if isinstance(node, Constant):
        return [node]
    if isinstance(node, (list, tuple, deque)):
        return [c for child in node for c in find_constants(child)]
    if hasattr(node, "__dataclass_fields__"):
        return [
            c
            for name in node.__dataclass_fields__
            for c in find_constants(getattr(node, name))
        ]
    return []


def test_parser_captures_source_text():
    (line,) = AST_Parser()("b = 2.50 * 1e3 + 1_000")
    constants = find_constants(line.expression_tree)
    assert [c.source_text for c in constants] == ["2.50", "1e3", "1_000"]
    assert not any(c.calculated for c in constants)


def test_reify_marks_calculated():
    node = _reify(3.14159)
    assert node.calculated
    assert node.source_text == ""


def test_source_text_ignored_in_equality():
    assert Constant(value=1000.0, source_text="1e3") == Constant(value=1000.0)


def test_format_code_skips_literals():
    rendered = HandCalcs(PlainTextRenderer())(
        "a = 3.14159\nb = 2 * a**2 + 0.50  # hc: -f .3f"
    )
    assert "b = 2 * a² + 0.50 = 2 * 3.142² + 0.50 = 20.239" in rendered


def test_format_code_applies_to_param_values():
    rendered = HandCalcs(PlainTextRenderer())("a = 3.14159  # hc: -f .2f")
    assert rendered.strip() == "a = 3.14"


def test_html_exponent_is_not_formatted():
    rendered = HandCalcs(HTMLRenderer())("a = 3.0\nb = a**2  # hc: -f .3f")
    assert "<sup>2</sup>" in rendered
    assert "2.000" not in rendered


def test_non_numeric_literals_unchanged():
    rendered = HandCalcs(PlainTextRenderer())("a = True\nb = 'text'")
    assert "a = True" in rendered
    assert "b = text" in rendered


def test_underscores_dropped():
    rendered = HandCalcs(PlainTextRenderer())("a = 2.0\nb = 1_000 * a")
    assert "b = 1000 * a = 1000 * 2 = 2000" in rendered


def test_latex_literals_keep_digits_and_typeset_exponents():
    rendered = HandCalcs(LatexRenderer())(
        "a = 3.14159\nb = 2 * a**2 + 0.50 * 2.5E-3 * 1e3  # hc: -f .3f"
    )
    assert "2 \\cdot a^{2} + 0.50 \\cdot 2.5 \\times 10^{-3} \\cdot 10^{3}" in rendered
    assert "3.142^{2}" in rendered
    assert "2.000" not in rendered


def test_latex_non_decimal_literal_not_typeset():
    rendered = HandCalcs(LatexRenderer())("a = 2\nb = 0xe5 * a")
    assert "0xe5 \\cdot a" in rendered


def test_markdown_exponent_is_not_formatted():
    rendered = HandCalcs(MarkdownRenderer())("a = 2.0\nb = a**2  # hc: -f .3f")
    assert "a^{2} = 2.000^{2} = 4.000" in rendered
