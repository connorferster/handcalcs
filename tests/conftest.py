"""
Shared scaffolding for the handcalcs v2 unit tests.

The tests in this suite exercise nodes and the ``BaseRenderer`` in isolation:
nodes are constructed directly (not produced by the parser) and rendered
through a bare ``BaseRenderer`` with a controlled context. This keeps
node/render behavior decoupled from parser correctness (covered by
``test_parser.py``) and keeps the concrete renderers out of scope.
"""
import pytest

from handcalcs.renderers.base import BaseRenderer, RenderContext, BaseRenderContext


# Sensible global-context defaults for rendering a single node in isolation.
# ``format_code`` is the constructor kwarg that populates ``RenderContext.format``.
_DEFAULT_GLOBALS = dict(
    space=" ",
    newline="\n",
    indent="    ",
    equality="=",
    mode="full",
    format_code=".5g",
)


@pytest.fixture
def renderer():
    """A fresh, un-subclassed ``BaseRenderer`` instance."""
    return BaseRenderer()


@pytest.fixture
def make_context():
    """
    Factory building a ``BaseRenderContext`` for isolated node rendering.

    ``line`` is a dict of line-context keys (e.g. ``{"current_mode": "sym"}``);
    any other keyword overrides a global-context default.
    """
    def _factory(*, line=None, **global_overrides):
        globals_ = {**_DEFAULT_GLOBALS, **global_overrides}
        line_ctx = RenderContext(**line) if line else RenderContext()
        return BaseRenderContext(RenderContext(**globals_), line_ctx)

    return _factory


@pytest.fixture
def render(renderer, make_context):
    """
    One-liner render helper.

    All overrides are placed on the *line* context, not the global one. This
    is deliberate: ``BaseRenderContext.current`` overlays the line context over
    the global context via ``ChainMap``, and a ``RenderContext()`` is always
    fully populated with defaults -- so a line-context value always wins over
    the corresponding global-context value. Putting per-test overrides
    (including ``current_mode``, required by ``Name``) on the line layer is the
    only way for them to take effect::

        render(Constant(4))
        render(Name("alpha", 3), current_mode="num")
        render(node, mode="sym", format_code=".2f")
    """
    def _render(node, *, current_mode=None, **overrides):
        line = dict(overrides)
        if current_mode is not None:
            line["current_mode"] = current_mode
        ctx = make_context(line=line or None)
        return renderer.render(node, ctx)

    return _render
