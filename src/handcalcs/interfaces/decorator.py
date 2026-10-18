__all__ = ["handcalc"]

import ast
import inspect
import textwrap
from typing import Optional
from functools import wraps
import innerscope
from ..renderers.base import BaseRenderer
from ..parsing.sequence import HcSequence
from .. import config


def function_body_source(func) -> str:
    """
    The source of ``func``'s body, dedented, without its decorators and ``def``
    line: the calculation the decorator renders.

    The comment lines directly above the first statement belong to the body (a
    heading or a note opening the calculation). ``inspect.getsource`` returns a
    nested function or a method still indented, so it is dedented before
    parsing.
    """
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    node = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func.__name__
    )
    lines = source.splitlines()
    first = node.body[0]
    if first.lineno == node.lineno:
        # A one-line def (``def f(x): return x * 2``): the body shares the def line.
        return "\n".join(ast.get_source_segment(source, stmt) for stmt in node.body)
    start = first.lineno - 1
    while start - 1 >= node.lineno and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    return textwrap.dedent("\n".join(lines[start:node.end_lineno]))


def handcalc(
    renderer: BaseRenderer, render_context: Optional[dict] = None
):
    if render_context is None:
        render_context = {}
    # Global config settings (format_code + any custom fields) seed the render
    # context, matching HandCalcs; the renderer-selection options are irrelevant
    # here because the renderer is supplied explicitly. An explicit
    # render_context wins.
    context_settings = {
        key: value
        for key, value in config.get_config().items()
        if key not in config.RENDERER_OPTIONS
    }

    def handcalc_decorator(func):
        body_source = function_body_source(func)

        @wraps(func)
        def decorated(*args, **kwargs):
            # innerscope retrieves values of locals, closures, and globals
            scope = innerscope.call(func, *args, **kwargs)
            hc_ast = HcSequence.from_source(body_source, hc_globals=scope, hc_locals={})
            base_context = renderer.create_context(**(context_settings | render_context | {"global_ns": scope}))
            rendered_tree = renderer.render(hc_ast, base_context)
            completed_render = renderer.complete(rendered_tree, base_context)
            return scope.return_value, completed_render
        return decorated
    return handcalc_decorator
