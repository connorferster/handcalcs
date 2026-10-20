import sys
from string import Formatter
from typing import Any
from .object_oriented import HandCalcs
from handcalcs import config
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

    # The IPython display class for each built-in renderer's output. A custom
    # renderer uses the display class of its nearest built-in ancestor.
    _DISPLAY = {
        "markdown": Markdown,
        "latex": Latex,
        "html": HTML,
        "ascii": Pretty,
        "base": Pretty,
    }

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


def display_class_for(renderer_cls: type[BaseRenderer]) -> type:
    """The display class of the renderer's nearest built-in ancestor (or itself)."""
    for cls in renderer_cls.__mro__:
        name = cls.__dict__.get("name")
        if name in _DISPLAY:
            return _DISPLAY[name]
    return Pretty


def resolve_jupyter_renderer(name: str) -> type[BaseRenderer]:
    """The renderer class registered under ``name``, or a ValueError naming the options."""
    renderer_cls = get_renderer(name)
    if renderer_cls is None:
        raise ValueError(
            f"No renderer named '{name}' is registered. Built-in renderers: "
            f"{', '.join(repr(name) for name in _DISPLAY if name != 'base')}. A custom "
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


def jupyter_handcalcs() -> tuple[HandCalcs, type]:
    """A HandCalcs with the session's Jupyter renderer, and its display class."""
    renderer_name = config.get_option(
        "jupyter_renderer", config.DEFAULTS["jupyter_renderer"]
    )
    renderer_cls = resolve_jupyter_renderer(renderer_name)
    return HandCalcs(renderer=renderer_cls()), display_class_for(renderer_cls)


def render_and_display(source: str, namespace: dict, result: Any = None) -> None:
    """
    Render ``source``, which has run in ``namespace``, with the session's
    Jupyter renderer and display it. ``result`` is the value of its last bare
    expression, if any (see ``HandCalcs.render_cell``).
    """
    hc, display_class = jupyter_handcalcs()
    # Display, but not as an "output"
    display(display_class(hc.render_cell(source, namespace, result)))


@register_line_cell_magic
@needs_local_scope
def render(line, cell=None, local_ns=None):
    """
    ``%%render`` runs its cell and renders all of it. ``%render <line>`` runs and
    renders just that one line (e.g. the one important equation in a longer cell),
    leaving the rest of the cell unrendered. ``%%render inputs=case`` runs and
    renders the cell with the values in the dict ``case`` in place of the values
    the cell assigns them (``strict=`` and ``allow_computed=`` may follow, as for
    ``HandCalcs(..., inputs=...)``).
    """
    if cell is None:
        return render_line(line, local_ns)
    arguments = input_arguments(line, local_ns)
    if arguments is not None:
        return render_with_inputs(cell, **arguments)
    # if line_args["sympy"]:
    #     cell = s_kit.convert_sympy_cell_to_py_cell(cell, user_ns_prerun)

    # Run the cell
    with cell_capture:
        exec_result = ip.run_cell(cell)

    if not exec_result.success:
        return None

    # Render against the updated variables (after .run_cell(cell)). The cell's
    # result (what IPython stores in ``_``) is the value of a last bare
    # expression, so it is shown without running the expression again.
    render_and_display(cell, ip.user_ns, exec_result.result)


INPUT_ARGUMENTS = ("inputs", "strict", "allow_computed")


def input_arguments(line: str, local_ns: dict | None) -> dict | None:
    """
    The arguments of ``%%render inputs=case, strict=False``, written as keyword
    arguments of a Python call and evaluated in the user namespace. None for a
    line without arguments (or with only words, like v1's ``%%render params``,
    which 2.0 ignores).
    """
    if "=" not in line:
        return None
    try:
        arguments = eval(
            f"__hc_arguments__({line.strip()})",
            ip.user_ns,
            {**(local_ns or {}), "__hc_arguments__": lambda **kwargs: kwargs},
        )
    except (SyntaxError, TypeError) as error:
        raise UsageError(
            f"%%render could not read its arguments '{line.strip()}' ({error}). "
            "Write them as keyword arguments, e.g. %%render inputs=case, strict=False"
        ) from None
    unknown = [name for name in arguments if name not in INPUT_ARGUMENTS]
    if unknown:
        raise UsageError(
            f"%%render does not take {', '.join(map(repr, unknown))}. Its arguments "
            f"are {', '.join(INPUT_ARGUMENTS)}."
        )
    if "inputs" not in arguments:
        raise UsageError(
            "%%render needs inputs=... when it is given strict or allow_computed."
        )
    if not isinstance(arguments["inputs"], dict):
        raise UsageError(
            f"%%render inputs= must be a dict, not {type(arguments['inputs']).__name__}."
        )
    return arguments


def render_with_inputs(
    cell: str, inputs: dict, strict: bool = True, allow_computed: bool = False
) -> None:
    """
    ``%%render inputs=case``: run and render the cell with the values in ``case``
    in place of the values the cell assigns them, as ``HandCalcs(...,
    inputs=case)`` does for a script.
    """
    binding = InputBinding(cell, inputs, strict=strict, allow_computed=allow_computed)
    ip.user_ns.update(binding.namespace())
    with cell_capture:
        exec_result = ip.run_cell(binding.exec_source)
    if not exec_result.success:
        ip.user_ns.pop(RESOLVER, None)
        return None
    hc, display_class = jupyter_handcalcs()
    display(display_class(hc.render_bound(binding, ip.user_ns)))


def render_line(line: str, local_ns: dict | None) -> None:
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
    try:
        # A bare expression is evaluated (once) for its result, as for ``_``.
        code = compile(source + "\n", "<%render>", "eval")
    except SyntaxError:
        exec(compile(source + "\n", "<%render>", "exec"), ip.user_ns)
        result = None
    else:
        result = eval(code, ip.user_ns)
    render_and_display(source + "\n", ip.user_ns, result)


def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, "line_cell")
