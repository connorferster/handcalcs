import os
import re
import sys
from string import Formatter
from .object_oriented import HandCalcs
from .display import DISPLAY_CLASS_NAMES, display_class_for
from handcalcs import config
from typing import Any, Optional
from handcalcs.parsing import line_values, sympy_substitution
from handcalcs.parsing.inputs import RESOLVER, InputBinding

# Importing the package registers the built-in renderers by name.
from handcalcs.renderers import BaseRenderer, get_renderer


class HandCalcsJupyterEnvironmentError(Exception):
    pass


try:
    from IPython.core.magic import (
        Magics,
        magics_class,
        cell_magic,
        needs_local_scope,
        register_line_cell_magic,
        register_line_magic,
    )
    from IPython.core.error import UsageError
    from IPython import get_ipython
    from IPython.display import Latex, HTML, Markdown, Pretty, display
    from IPython.utils.capture import capture_output

except ImportError:
    raise HandCalcsJupyterEnvironmentError(
        "The Jupyter interface (handcalcs.render) must be used in a Python environment where IPython installed."
    )


try:
    ip = get_ipython()
    cell_capture = capture_output(stdout=True, stderr=True, display=True)
except AttributeError:
    raise HandCalcsJupyterEnvironmentError(
        "The Jupyter interface (handcalcs.render) must be used in a Python environment where IPython installed."
        " Try using the object-oriented interface instead."
    )


@register_line_magic
def hc_format_code(line):
    try:
        list(Formatter().parse(line))
    except ValueError as e:
        raise e
    config.set_option("format_code", line)


def resolve_jupyter_renderer(name: str) -> type[BaseRenderer]:
    """The renderer class registered under ``name``, or a ValueError naming the options."""
    renderer_cls = get_renderer(name)
    if renderer_cls is None:
        raise ValueError(
            f"No renderer named '{name}' is registered. Built-in renderers: "
            f"{', '.join(repr(name) for name in DISPLAY_CLASS_NAMES if name != 'base')}. A custom "
            "renderer must be imported (defined) before it can be selected by name."
        )
    return renderer_cls


@register_line_magic
def hc_default_renderer(line):
    """
    Set the renderer used by ``%%render`` for this session (the ``jupyter_renderer``
    option; ``handcalcs.save_config()`` makes it permanent). ``default_renderer``,
    which a bare ``HandCalcs()`` uses, is not changed.
    """
    name = line.strip()
    resolve_jupyter_renderer(name)
    config.set_option("jupyter_renderer", name)


def jupyter_handcalcs(renderer_name: Optional[str] = None) -> tuple[HandCalcs, type]:
    """
    A HandCalcs with the renderer named ``renderer_name`` (by default the
    session's Jupyter renderer), and its display class.
    """
    if renderer_name is None:
        renderer_name = config.get_option(
            "jupyter_renderer", config.DEFAULTS["jupyter_renderer"]
        )
    renderer_cls = resolve_jupyter_renderer(renderer_name)
    return HandCalcs(renderer=renderer_cls()), display_class_for(renderer_cls)


def render_and_display(
    source: str,
    namespace: dict,
    values: Optional[line_values.LineValues] = None,
    destination: Optional[str | os.PathLike] = None,
    as_source: bool = False,
    renderer_name: Optional[str] = None,
) -> None:
    """
    Render ``source``, which has run in ``namespace``, with the session's
    Jupyter renderer (or the one named ``renderer_name``) and display it (or
    write it to ``destination``, or print its source, see ``show``). ``values``
    are the values recorded while it ran; without them, every line shows the
    values in ``namespace``.
    """
    hc, display_class = jupyter_handcalcs(renderer_name)
    rendered = hc.render_run(source, namespace, values)
    show(hc, display_class, rendered, destination, as_source)


def show(
    hc: HandCalcs,
    display_class: type,
    rendered: Any,
    destination: Optional[str | os.PathLike],
    as_source: bool = False,
) -> None:
    """
    Display ``rendered`` (but not as an "output"), or, with a ``destination``,
    write it to that file instead and display the file's path. With
    ``as_source`` (``%%source``), print the rendered text itself instead, to
    be read or copied, e.g. the LaTeX to paste into a document.
    """
    if as_source:
        print_source(hc, rendered)
        return
    if destination is None:
        display(display_class(rendered))
        return
    path = hc.renderer.to_file(rendered, destination)
    display(Pretty(f"Rendered to {path}"))


def print_source(hc: HandCalcs, rendered: Any) -> None:
    """Print the text a renderer produced; a document or workbook has none."""
    if not isinstance(rendered, str):
        raise UsageError(
            f"%%source shows the text a renderer produces, but "
            f"{type(hc.renderer).__name__} produces a {type(rendered).__name__}. "
            'Use %%render destination="..." to write it to a file instead.'
        )
    print(rendered, end="" if rendered.endswith("\n") else "\n")


def run_recorded(source: str) -> tuple[Any, Optional[line_values.LineValues]]:
    """
    Run ``source`` as a cell (its own output captured), recording its values
    line by line. Returns IPython's result and the values, or None for the
    values when the cell can't be parsed as Python after IPython's transforms,
    or with the 'line_values' option off.
    """
    values = None
    if config.get_option("line_values", True):
        try:
            values = line_values.LineValues(ip.transform_cell(source))
        except SyntaxError:
            pass
    if values is None:
        with cell_capture:
            return ip.run_cell(source), None
    with cell_capture, line_values.recording(values, is_cell_frame):
        exec_result = ip.run_cell(source)
    return exec_result, values


def run_staged(source: str) -> tuple[Any, Optional[line_values.LineValues], str]:
    """
    Run a cell with '# hc: -y' lines a piece at a time (see
    sympy_substitution.run_staged): each line is rewritten just before it runs.
    Returns IPython's result for the last piece that ran, the values recorded
    line by line (None with the 'line_values' option off) and the rewritten cell.
    """
    __tracebackhide__ = True
    # IPython's transforms (line magics, !commands) keep each line on its line,
    # so the transformed cell and the cell have the same line numbers.
    transformed = ip.transform_cell(source)
    results = []

    def run_chunk(chunk: str) -> bool:
        result = ip.run_cell(chunk)
        results.append(result)
        return result.success

    values = None
    if config.get_option("line_values", True):
        values = line_values.LineValues(transformed)
    substitutions = []

    def on_substitution(substitution) -> None:
        substitutions.append(substitution)
        if values is not None:
            values.add_names(substitution.line, substitution.names)

    try:
        with cell_capture:
            if values is None:
                rewritten = sympy_substitution.run_staged(
                    transformed, ip.user_ns, run_chunk, on_substitution
                )
            else:
                with line_values.recording(values, is_cell_frame):
                    rewritten = sympy_substitution.run_staged(
                        transformed, ip.user_ns, run_chunk, on_substitution
                    )
    except sympy_substitution.SympySubstitutionError as error:
        raise UsageError(str(error)) from None
    return results[-1], values, carry_lines(source, transformed, rewritten)


def carry_lines(source: str, transformed: str, rewritten: str) -> str:
    """
    'source' with the lines that differ between 'transformed' and 'rewritten'
    (the '# hc: -y' lines, which IPython's transforms leave as they are) taken
    from 'rewritten'.
    """
    lines = source.splitlines(keepends=True)
    before = transformed.splitlines(keepends=True)
    after = rewritten.splitlines(keepends=True)
    for index, (old, new) in enumerate(zip(before, after)):
        if old != new and index < len(lines):
            ending = lines[index][len(lines[index].rstrip("\r\n")) :]
            lines[index] = new.rstrip("\r\n") + ending
    return "".join(lines)


def is_cell_frame(frame) -> bool:
    """True for the frame of a cell's code (not of a function or module it calls)."""
    return frame.f_globals is ip.user_ns and frame.f_code.co_name == "<module>"


@register_line_cell_magic
@needs_local_scope
def render(line, cell=None, local_ns=None):
    """
    ``%%render`` runs its cell and renders all of it. ``%render <line>`` runs and
    renders just that one line (e.g. the one important equation in a longer cell),
    leaving the rest of the cell unrendered. ``%%render inputs=case`` runs and
    renders the cell with the values in the dict ``case`` in place of the values
    the cell assigns them (``strict=`` and ``allow_computed=`` may follow, as for
    ``HandCalcs(..., inputs=...)``). ``%%render destination="calc.tex"`` writes
    the render to that file instead of displaying it.
    """
    __tracebackhide__ = True  # IPython leaves this frame out of a traceback
    run_and_render(line, cell, local_ns)


@register_line_cell_magic("source")
@needs_local_scope
def source_magic(line, cell=None, local_ns=None):
    """
    ``%%source`` runs its cell and renders it as ``%%render`` does, but prints
    the rendered text (the LaTeX, Markdown, HTML, ...) instead of displaying
    it, so it can be read or copied into another document. ``%%source latex``
    uses the renderer named ``latex`` for this cell (v1's ``%%tex``); without a
    name it uses the session's renderer. It takes ``%%render``'s ``inputs=``,
    ``strict=`` and ``allow_computed=``, and ``renderer="latex"`` with them.
    ``%source <line>`` prints the render of one line.
    """
    __tracebackhide__ = True
    run_and_render(line, cell, local_ns, as_source=True)


def run_and_render(
    line: str, cell: Optional[str], local_ns: dict | None, as_source: bool = False
) -> None:
    """``%%render`` and ``%%source`` (``as_source``), cell or line magic."""
    __tracebackhide__ = True
    if as_source:
        line, renderer_name = source_renderer(line, cell is None)
    else:
        renderer_name = None
    if cell is None:
        return render_line(line, local_ns, as_source, renderer_name)
    arguments = render_arguments(line, local_ns, as_source)
    renderer_name = arguments.pop("renderer", renderer_name)
    destination = arguments.pop("destination", None)
    if arguments:
        return render_with_inputs(
            cell,
            **arguments,
            destination=destination,
            as_source=as_source,
            renderer_name=renderer_name,
        )

    # Run the cell. Its own output is captured so that only the render shows;
    # an error is raised again, so that it is shown (and stops "Run All") as it
    # would be in a cell without %%render.
    if sympy_substitution.has_sympy_commands(cell):
        exec_result, values, cell = run_staged(cell)
    else:
        exec_result, values = run_recorded(cell)
    exec_result.raise_error()

    # Render against the updated variables (after .run_cell(cell))
    render_and_display(cell, ip.user_ns, values, destination, as_source, renderer_name)


def source_renderer(line: str, is_line_magic: bool) -> tuple[str, Optional[str]]:
    """
    Split ``%%source latex`` into the rest of the line and the renderer name.
    A line magic's line is code, so only the cell magic takes a name.
    """
    match = re.match(r"\s*([A-Za-z_][\w.-]*)(?![\w.-])\s*(?:,|$|(?=[^=\s]))", line)
    if is_line_magic or match is None:
        return line, None
    name = match.group(1)
    resolve_magic_renderer(name)
    return line[match.end() :].strip(), name


def resolve_magic_renderer(name: str) -> None:
    """A UsageError (shown without a traceback) for an unknown renderer name."""
    try:
        resolve_jupyter_renderer(name)
    except ValueError as error:
        raise UsageError(str(error)) from None


RENDER_ARGUMENTS = ("inputs", "strict", "allow_computed", "destination")
SOURCE_ARGUMENTS = ("inputs", "strict", "allow_computed", "renderer")


def render_arguments(line: str, local_ns: dict | None, as_source: bool = False) -> dict:
    """
    The arguments of ``%%render inputs=case, strict=False, destination="c.tex"``
    (or of ``%%source``), written as keyword arguments of a Python call and
    evaluated in the user namespace. Empty for a line without arguments (or
    with only words, like v1's ``%%render params``, which 2.0 ignores).
    """
    magic = "%%source" if as_source else "%%render"
    allowed = SOURCE_ARGUMENTS if as_source else RENDER_ARGUMENTS
    if "=" not in line:
        return {}
    try:
        arguments = eval(
            f"__hc_arguments__({line.strip()})",
            ip.user_ns,
            {**(local_ns or {}), "__hc_arguments__": lambda **kwargs: kwargs},
        )
    except (SyntaxError, TypeError) as error:
        raise UsageError(
            f"{magic} could not read its arguments '{line.strip()}' ({error}). "
            f"Write them as keyword arguments, e.g. {magic} inputs=case, strict=False"
        ) from None
    unknown = [name for name in arguments if name not in allowed]
    if unknown:
        hint = (
            " %%source prints the render; use %%render to write a file."
            if as_source and "destination" in unknown
            else ""
        )
        raise UsageError(
            f"{magic} does not take {', '.join(map(repr, unknown))}. Its arguments "
            f"are {', '.join(allowed)}.{hint}"
        )
    if "inputs" not in arguments and ({"strict", "allow_computed"} & set(arguments)):
        raise UsageError(
            f"{magic} needs inputs=... when it is given strict or allow_computed."
        )
    if "inputs" in arguments and not isinstance(arguments["inputs"], dict):
        raise UsageError(
            f"{magic} inputs= must be a dict, not {type(arguments['inputs']).__name__}."
        )
    if "renderer" in arguments:
        resolve_magic_renderer(arguments["renderer"])
    return arguments


def render_with_inputs(
    cell: str,
    inputs: dict,
    strict: bool = True,
    allow_computed: bool = False,
    destination: Optional[str | os.PathLike] = None,
    as_source: bool = False,
    renderer_name: Optional[str] = None,
) -> None:
    """
    ``%%render inputs=case``: run and render the cell with the values in ``case``
    in place of the values the cell assigns them, as ``HandCalcs(...,
    inputs=case)`` does for a script.
    """
    __tracebackhide__ = True
    if sympy_substitution.has_sympy_commands(cell):
        raise UsageError(
            "'# hc: -y' can't be combined with inputs=: it rewrites lines just "
            "before they run, and inputs= rewrites the cell before it runs."
        )
    binding = InputBinding(cell, inputs, strict=strict, allow_computed=allow_computed)
    ip.user_ns.update(binding.namespace())
    exec_result, values = run_recorded(binding.exec_source)
    if not exec_result.success:
        ip.user_ns.pop(RESOLVER, None)
        exec_result.raise_error()
    hc, display_class = jupyter_handcalcs(renderer_name)
    rendered = hc.render_bound(binding, ip.user_ns, values)
    show(hc, display_class, rendered, destination, as_source)


def render_line(
    line: str,
    local_ns: dict | None,
    as_source: bool = False,
    renderer_name: Optional[str] = None,
) -> None:
    """
    ``%render``: run one line of code in the user namespace, then render it.

    The line runs at the top level of a cell (also inside a top-level ``for`` or
    ``if``). Inside a function the line's variables could not become the
    function's local variables, so that is refused; render a function with
    ``@handcalc`` instead.
    """
    source = line.strip()
    if not source:
        raise UsageError("%render needs a line of code to run, e.g. %render c = a + b")
    if local_ns is not None and local_ns is not ip.user_ns:
        raise UsageError(
            "%render can't be used inside a function: the line's variables would "
            "not be the function's variables. Decorate the function with "
            "@handcalc to render it."
        )
    if sympy_substitution.has_sympy_commands(source):
        # '%render x = f  # hc: -y': the line runs as 'x = <f's expression>'.
        try:
            source, _ = sympy_substitution.substitute(
                source,
                sympy_substitution.namespace_lookup(ip.user_ns),
                check_lines=frozenset({1}),
            )
        except sympy_substitution.SympySubstitutionError as error:
            raise UsageError(str(error)) from None
    exec(compile(source + "\n", "<%render>", "exec"), ip.user_ns)
    render_and_display(
        source + "\n", ip.user_ns, as_source=as_source, renderer_name=renderer_name
    )


def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, "line_cell")
    ipython.register_magic_function(source_magic, "line_cell", "source")
