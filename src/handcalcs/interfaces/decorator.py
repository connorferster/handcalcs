__all__ = ["handcalc"]

import ast
import inspect
import textwrap
from typing import Optional
from functools import wraps
import innerscope
from ..renderers.base import BaseRenderer
from ..parsing.sequence import HcSequence, drop_after_return
from ..parsing.line_values import LineValues, recording
from .. import config


def function_body_source(func) -> str:
    """The source of ``func``'s body (see ``function_body``)."""
    return function_body(func)[0]


def function_body(func) -> tuple[str, int]:
    """
    The source of ``func``'s body, dedented, without its decorators and ``def``
    line: the calculation the decorator renders. Also the number to add to a
    line number of that source to give the line in ``func``'s file.

    The comment lines directly above the first statement belong to the body (a
    heading or a note opening the calculation). A final ``return`` that only
    names values (``return M`` or ``return M, V``) is left out: the body already
    shows them. ``inspect.getsource`` returns a nested function or a method
    still indented, so it is dedented before parsing.
    """
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == func.__name__
    )
    lines = source.splitlines()
    # ``getsource`` starts at the first line of the code object (its first
    # decorator, if any).
    file_offset = func.__code__.co_firstlineno - 1
    first = node.body[0]
    if first.lineno == node.lineno:
        # A one-line def (``def f(x): return x * 2``): the body shares the def line.
        body = "\n".join(ast.get_source_segment(source, stmt) for stmt in node.body)
        return body, file_offset + node.lineno - 1
    start = first.lineno - 1
    while start - 1 >= node.lineno and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    end = node.end_lineno
    last = node.body[-1]
    if len(node.body) > 1 and returns_names_only(last):
        end = last.lineno - 1
    return textwrap.dedent("\n".join(lines[start:end])), file_offset + start


def returns_names_only(stmt: ast.stmt) -> bool:
    """True for ``return``, ``return M`` and ``return M, V``."""
    if not isinstance(stmt, ast.Return):
        return False
    if stmt.value is None:
        return True
    values = stmt.value.elts if isinstance(stmt.value, ast.Tuple) else [stmt.value]
    return all(isinstance(value, ast.Name) for value in values)


def handcalc(renderer: BaseRenderer, render_context: Optional[dict] = None):
    if render_context is None:
        render_context = {}
    # Global config settings (format_code + any custom fields) seed the render
    # context, matching HandCalcs; the renderer-selection options are irrelevant
    # here because the renderer is supplied explicitly. An explicit
    # render_context wins.
    context_settings = {
        key: value
        for key, value in config.get_config().items()
        if key not in config.NON_CONTEXT_OPTIONS
    }

    def handcalc_decorator(func):
        body_source, line_offset = function_body(func)
        code = func.__code__

        def is_call_frame(frame) -> bool:
            # innerscope runs a copy of the function's code, made to keep its locals.
            frame_code = frame.f_code
            return (
                frame_code.co_name == code.co_name
                and frame_code.co_firstlineno == code.co_firstlineno
                and frame_code.co_filename == code.co_filename
            )

        @wraps(func)
        def decorated(*args, **kwargs):
            # innerscope retrieves values of locals, closures, and globals; the
            # values of each line are recorded while it runs.
            if config.get_option("line_values", True):
                values = LineValues(body_source, line_offset)
                with recording(values, is_call_frame):
                    scope = innerscope.call(func, *args, **kwargs)
            else:
                values = None
                scope = innerscope.call(func, *args, **kwargs)
            hc_ast = HcSequence.from_source(
                body_source, hc_globals=scope, hc_locals={}, line_values=values
            )
            drop_after_return(hc_ast.sequence)
            base_context = renderer.create_context(
                **(context_settings | render_context | {"global_ns": scope})
            )
            rendered_tree = renderer.render(hc_ast, base_context)
            completed_render = renderer.complete(rendered_tree, base_context)
            return scope.return_value, completed_render

        return decorated

    return handcalc_decorator
