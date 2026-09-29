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
