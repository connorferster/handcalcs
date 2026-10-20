"""
Tests for the result of a bare expression statement (#54): ``2 + 2`` renders as
``2 + 2 = 4``. The parser evaluates the expression in the namespace when that has
no side effects (it calls only pure functions); otherwise the line shows its
symbolic and numeric forms only, as before.
"""
import math

import pytest

from handcalcs import HandCalcs
from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.parsing.null_values import NoValue
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.ascii import ASCIIRenderer


def _value(source, names=None):
    return AST_Parser(globals=names or {})(source)[0].value


def _render(renderer, source):
    names = {}
    exec(source, names)
    return HandCalcs(renderer)(source, names)


@pytest.mark.parametrize(
    "source, expected",
    [
        ("2 + 2\n", 4),
        ("a * b\n", 6),
        ("a\n", 2),
        ("max(a, b) + abs(-a)\n", 5),
        ("math.sqrt(a * 8)\n", 4.0),
        ("sqrt(a * 8)\n", 4.0),
        ("[x**2 for x in (a, b)]\n", [4, 9]),
    ],
)
def test_parser_evaluates_pure_expression(source, expected):
    names = {"a": 2, "b": 3, "math": math, "sqrt": math.sqrt}
    assert _value(source, names) == expected


@pytest.mark.parametrize(
    "source",
    [
        "show(a)\n",  # a side effect: must not run twice
        "items.append(a)\n",  # a method call
        "f(a)\n",  # a user function
        "(y := a)\n",  # an assignment expression
        "a / 0\n",  # evaluating fails
        "missing + 1\n",  # a name that is not in the namespace
        '"a docstring"\n',
    ],
)
def test_parser_leaves_impure_or_failing_expression_unevaluated(source):
    calls = []
    names = {"a": 2, "items": [], "f": calls.append, "show": calls.append}
    assert isinstance(_value(source, names), NoValue)
    assert calls == [] and names["items"] == []


def test_return_has_no_value():
    tree = AST_Parser(globals={"a": 2})("def f():\n    return a + 1\n")
    assert all(isinstance(getattr(n, "value", NoValue()), NoValue) for n in tree)


def test_plaintext_expression_results():
    out = _render(ASCIIRenderer(), "a = 2\nb = 3\n2 + 2\na * b\na\n")
    assert out.splitlines()[2:] == ["2 + 2 = 4", "a * b = 2 * 3 = 6", "    a = 2"]


def test_impure_expression_has_no_result():
    out = _render(ASCIIRenderer(), "a = 2\nitems = []\nitems.append(a)\n")
    assert out.splitlines()[-1] == "items.append(a) = items.append(2)"


def test_expression_inline_comment_and_format_command():
    out = _render(
        ASCIIRenderer(), "a = 2\nb = 3\na / b  # hc: -f .3f\na * b  # area\n"
    )
    assert out.splitlines()[2:] == [
        "a / b = 2.000 / 3.000 = 0.667",
        "a * b = 2 * 3 = 6 (area)",
    ]


def test_latex_expression_result_aligns_on_first_equals():
    out = _render(LatexRenderer(), "a = 2\nb = 3\na * b\n")
    assert "a \\cdot b &= 2 \\cdot 3 = 6" in out


def test_html_expression_result_is_highlighted():
    out = _render(HTMLRenderer(), "a = 2\nb = 3\na * b\n")
    assert 'a · b = 2 · 3 = <span class="hc-result">6</span>' in out


def test_param_command_hides_substitution():
    out = _render(ASCIIRenderer(), "a = 2\nb = 3\na * b  # hc: -p\n")
    assert out.splitlines()[-1] == "a * b = 6"
