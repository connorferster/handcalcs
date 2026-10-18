"""
Integration tests for the ``@handcalc`` decorator.

The decorator runs the wrapped function via ``innerscope`` (capturing its
locals), re-parses the function source, and renders it with the supplied
renderer. It returns ``(return_value, rendered)`` where the type of
``rendered`` is whatever the renderer's ``complete()`` produces: the raw
render tree (a list) for the ``BaseRenderer`` and a finished HTML string for
the ``HTMLRenderer``.
"""
from handcalcs import handcalc
from handcalcs.renderers import BaseRenderer, HTMLRenderer


# A single 6-line calculation function, decorated once per renderer. The body
# is deliberately simple so the assertions focus on the decorator wiring and
# the renderer's output type, not on rendering minutiae.
@handcalc(BaseRenderer())
def calc_base():
    a = 2
    b = 3
    c = a + b
    d = c * 2
    e = d - 1
    return e


@handcalc(HTMLRenderer())
def calc_html():
    a = 2
    b = 3
    c = a + b
    d = c * 2
    e = d - 1
    return e


def test_decorator_returns_value_and_render():
    # The decorator returns a (return_value, rendered) tuple; the return value
    # is the function's actual result, evaluated normally.
    value, rendered = calc_base()
    assert value == 9  # ((2 + 3) * 2) - 1
    assert rendered is not None


def test_base_renderer_returns_render_tree_list():
    # BaseRenderer.complete() returns the raw render tree (a nested list), not
    # joined text, so a caller can post-process before joining.
    _value, rendered = calc_base()
    assert isinstance(rendered, list)
    assert rendered  # non-empty


def test_html_renderer_returns_html_string():
    # HTMLRenderer.complete() joins the tree and wraps it, returning a finished
    # HTML string.
    value, rendered = calc_html()
    assert value == 9
    assert isinstance(rendered, str)
    assert rendered.startswith('<div class="handcalcs">')


# -- rendered content ---------------------------------------------------------
# The decorator renders the function *body*: not its decorators or def line.

from handcalcs.renderers import LatexRenderer, PlainTextRenderer


@handcalc(PlainTextRenderer())
def calc_plain():
    a = 2
    b = 3
    c = a + b
    d = c * 2
    e = d - 1
    return e


def test_body_is_rendered():
    _value, rendered = calc_plain()
    lines = rendered.splitlines()
    assert lines[:5] == [
        "a = 2",
        "b = 3",
        "c = a + b = 2 + 3 = 5",
        "d = c * 2 = 5 * 2 = 10",
        "e = d - 1 = 10 - 1 = 9",
    ]
    assert "def" not in rendered and "handcalc" not in rendered


def test_base_render_tree_holds_the_calc_lines():
    _value, rendered = calc_base()
    assert ["c", "=", "a + b", "=", "2 + 3", "=", "5"] in rendered[0][1]


def test_html_render_holds_the_calc_lines():
    _value, rendered = calc_html()
    assert '<div class="hc-line">c = a + b = 2 + 3 = <span class="hc-result">5</span></div>' in rendered


@handcalc(LatexRenderer())
def beam(w, L):
    """Simply supported beam."""
    # Midspan moment
    M = w * L**2 / 8  # kN m
    return M


def test_arguments_docstring_and_leading_comments_are_rendered():
    value, rendered = beam(5, 6)
    assert value == 22.5
    assert "Simply supported beam." in rendered
    assert "Midspan moment" in rendered
    assert r"M &= \frac{w \cdot L^{2}}{8} = \frac{5 \cdot 6^{2}}{8} = 22.5" in rendered


def test_nested_function_and_closure():
    # inspect.getsource returns a nested function indented; it used to raise
    # IndentationError.
    def outer(k):
        @handcalc(PlainTextRenderer())
        def inner(a):
            b = a * k
            return b
        return inner(4)

    value, rendered = outer(10)
    assert value == 40
    assert "b = a * k = 4 * 10 = 40" in rendered


def test_method():
    class Calc:
        @handcalc(PlainTextRenderer())
        def double(self, x):
            y = x * 2
            return y

    value, rendered = Calc().double(3)
    assert value == 6
    assert "y = x * 2 = 3 * 2 = 6" in rendered


def test_multiline_signature_and_comment_commands():
    @handcalc(PlainTextRenderer())
    def calc(
        a,
        # a comment inside the signature is not part of the body
        b=2,
    ):
        c = a + b  # hc: -f .2f
        return c

    value, rendered = calc(1)
    assert value == 3
    assert "a comment inside the signature" not in rendered
    assert "c = a + b = 1.00 + 2.00 = 3.00" in rendered


def test_one_line_function():
    @handcalc(PlainTextRenderer())
    def double(x): return x * 2

    value, rendered = double(3)
    assert value == 6
    assert rendered.strip() == "x * 2"
