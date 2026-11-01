"""Regression coverage for issue #339: function docstrings are not calculations."""

from handcalcs import handcalc
from handcalcs.renderers import MarkdownRenderer


def my_add(a: int, b: int) -> int:
    """Return sum of a and b"""
    c = a + b
    return c


def test_markdown_decorator_omits_function_docstring() -> None:
    assert my_add(7, 8) == 15
    value, rendered = handcalc(MarkdownRenderer())(my_add)(7, 8)

    assert value == 15
    assert isinstance(rendered, str)
    assert "c &= a + b = 7 + 8 = 15" in rendered
    assert my_add.__doc__ == "Return sum of a and b"
    assert "Return sum of a and b" not in rendered
