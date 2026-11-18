__all__ = ["handcalc"]

import ast
import inspect
import os
import textwrap
import warnings
from typing import Callable, Optional
from functools import wraps
import innerscope
from ..renderers.base import BaseRenderer
from .object_oriented import default_renderer
from .display import show
from ..parsing.sequence import HcSequence, drop_after_return
from ..parsing.line_values import LineValues, recording
from ..parsing import sympy_substitution
from .. import config


def function_body_source(func, docstring: bool = True) -> str:
    """The source of ``func``'s body (see ``function_body``)."""
    return function_body(func, docstring)[0]


def function_body(func, docstring: bool = True) -> tuple[str, int]:
    """
    The source of ``func``'s body, dedented, without its decorators and ``def``
    line: the calculation the decorator renders. Also the number to add to a
    line number of that source to give the line in ``func``'s file.

    The comment lines directly above the first statement belong to the body (a
    heading or a note opening the calculation). A final ``return`` that only
    names values (``return M`` or ``return M, V``) is left out: the body already
    shows them. ``inspect.getsource`` returns a nested function or a method
    still indented, so it is dedented before parsing.

    With ``docstring=False`` the docstring is left out too; the comment lines
    between it and the first statement are kept.
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
    statements = node.body
    has_docstring = ast.get_docstring(node, clean=False) is not None
    if not docstring and has_docstring:
        statements = statements[1:]
    if not statements:
        # Nothing but a docstring.
        return "", file_offset + node.end_lineno
    first = statements[0]
    if first.lineno == node.lineno:
        # A one-line def (``def f(x): return x * 2``): the body shares the def line.
        body = "\n".join(ast.get_source_segment(source, stmt) for stmt in statements)
        return body, file_offset + node.lineno - 1
    # The comment lines directly above the first statement; the scan stops at the
    # def line, or at the end of a docstring that is left out.
    floor = node.body[0].end_lineno if statements is not node.body else node.lineno
    start = first.lineno - 1
    while start - 1 >= floor and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    end = node.end_lineno
    last = statements[-1]
    if len(statements) > 1 and returns_names_only(last):
        end = last.lineno - 1
    return textwrap.dedent("\n".join(lines[start:end])), file_offset + start


class SympyFunction:
    """
    A function with ``# hc: -y`` lines, run as a copy with those lines rewritten
    (see handcalcs.parsing.sympy_substitution). The expressions are looked up in
    the call's arguments, then the function's globals, when it is called; the
    copy is compiled again only when one of them changes.
    """

    def __init__(self, func):
        if func.__code__.co_freevars:
            raise sympy_substitution.SympySubstitutionError(
                f"'{func.__name__}' uses variables of the function it is defined "
                "in, so its '# hc: -y' lines can't be rewritten: define it at the "
                "top level of a module or notebook."
            )
        self.func = func
        self.signature = inspect.signature(func)
        self.source = textwrap.dedent(inspect.getsource(func))
        self.marks = sympy_substitution.find_marks(self.source)
        self._key = None
        self._compiled = None

    def prepare(self, body_source: str, args, kwargs):
        """The function to call and its rewritten body source, for these arguments."""
        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()
        lookup = sympy_substitution.namespace_lookup(
            bound.arguments, self.func.__globals__
        )
        source, substitutions = sympy_substitution.substitute(
            self.source, lookup, marks=self.marks
        )
        body, _ = sympy_substitution.substitute(body_source, lookup)
        if not substitutions:
            return self.func, body
        if source != self._key:
            self._compiled = self.compile(source)
            self._key = source
        return self._compiled, body

    def compile(self, source: str):
        func = self.func
        tree = ast.parse(source)
        node = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == func.__name__
        )
        # The copy is not decorated again; its lines are the function's lines in
        # its file (``getsource`` starts at the first line of the code object).
        node.decorator_list = []
        module = ast.Module(body=[node], type_ignores=[])
        ast.increment_lineno(module, func.__code__.co_firstlineno - 1)
        code = compile(module, func.__code__.co_filename, "exec")
        namespace: dict = {}
        exec(code, func.__globals__, namespace)
        copy = namespace[func.__name__]
        copy.__defaults__ = func.__defaults__
        copy.__kwdefaults__ = func.__kwdefaults__
        return copy


def returns_names_only(stmt: ast.stmt) -> bool:
    """True for ``return``, ``return M`` and ``return M, V``."""
    if not isinstance(stmt, ast.Return):
        return False
    if stmt.value is None:
        return True
    values = stmt.value.elts if isinstance(stmt.value, ast.Tuple) else [stmt.value]
    return all(isinstance(value, ast.Name) for value in values)


def handcalc(
    renderer: Optional[BaseRenderer] = None,
    render_context: Optional[dict] = None,
    destination: Optional[str | os.PathLike] = None,
    *,
    docstring: bool = True,
    display: bool | Callable[[object], object] = False,
    jupyter_display: Optional[bool] = None,
):
    """
    Decorate a calculation function so that a call returns ``(return_value,
    rendered)``. Without a renderer, the ``default_renderer`` option's is used
    (the ASCIIRenderer unless set). Usable as ``@handcalc(renderer)``,
    ``@handcalc()`` or ``@handcalc``.

    If 'destination' is given, each call writes the render to that file (with
    the renderer's 'to_file', as ``HandCalcs(..., destination=)`` does) and
    returns ``(return_value, path)``, the path as a pathlib.Path.

    The function's docstring is rendered as a note above the calculation; with
    ``docstring=False`` it is left out (for a docstring written for the code's
    readers rather than for the calculation).

    With ``display=True`` each call shows the render where the code is running
    (displayed in a Jupyter kernel, printed elsewhere) and returns only the
    function's return value. ``display`` may instead be a function, which each
    call passes the render to (``display=st.markdown``). With a 'destination',
    the file's path is shown (or passed) instead of the render.
    ``jupyter_display=True`` is a deprecated alias for ``display=True``.
    """
    if jupyter_display is not None:
        if display is not False:
            raise TypeError("give display or jupyter_display, not both")
        warnings.warn(
            "jupyter_display is deprecated; use display=True, which shows the "
            "render in Jupyter and prints it elsewhere.",
            DeprecationWarning,
            stacklevel=2,
        )
        display = bool(jupyter_display)
    if not (isinstance(display, bool) or callable(display)):
        raise TypeError(f"display must be True, False or a function, not {display!r}")
    if callable(renderer) and not isinstance(renderer, BaseRenderer):
        # @handcalc without brackets: the "renderer" is the decorated function.
        return handcalc(docstring=docstring, display=display)(renderer)
    if renderer is None:
        renderer = default_renderer()
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
        body_source, line_offset = function_body(func, docstring)
        sympy_function = None
        if sympy_substitution.has_sympy_commands(body_source):
            sympy_function = SympyFunction(func)

        @wraps(func)
        def decorated(*args, **kwargs):
            run, source = func, body_source
            if sympy_function is not None:
                run, source = sympy_function.prepare(body_source, args, kwargs)
            code = run.__code__

            def is_call_frame(frame) -> bool:
                # innerscope runs a copy of the function's code, made to keep
                # its locals.
                frame_code = frame.f_code
                return (
                    frame_code.co_name == code.co_name
                    and frame_code.co_firstlineno == code.co_firstlineno
                    and frame_code.co_filename == code.co_filename
                )

            # innerscope retrieves values of locals, closures, and globals; the
            # values of each line are recorded while it runs.
            if config.get_option("line_values", True):
                values = LineValues(source, line_offset)
                with recording(values, is_call_frame):
                    scope = innerscope.call(run, *args, **kwargs)
            else:
                values = None
                scope = innerscope.call(run, *args, **kwargs)
            hc_ast = HcSequence.from_source(
                source, hc_globals=scope, hc_locals={}, line_values=values
            )
            drop_after_return(hc_ast.sequence)
            base_context = renderer.create_context(
                **(context_settings | render_context | {"global_ns": scope})
            )
            rendered_tree = renderer.render(hc_ast, base_context)
            completed_render = renderer.complete(rendered_tree, base_context)
            output = completed_render
            if destination is not None:
                output = renderer.to_file(completed_render, destination)
            if display is False:
                return scope.return_value, output
            if callable(display):
                display(output)
            elif destination is not None:
                print(f"Rendered to {output}")
            else:
                show(renderer, output)
            return scope.return_value

        return decorated

    return handcalc_decorator
