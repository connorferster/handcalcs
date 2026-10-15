import sys
from string import Formatter
from .object_oriented import HandCalcs
from handcalcs import config
# Importing the package registers the built-in renderers by name.
from handcalcs.renderers import BaseRenderer, get_renderer

class HandCalcsJupyterEnvironmentError(Exception):
    pass

try:
    from IPython.core.magic import (
        Magics,
        magics_class,
        cell_magic,
        register_cell_magic,
        register_line_magic,
    )
    from IPython import get_ipython
    from IPython.display import Latex, HTML, Markdown, Pretty, display
    from IPython.utils.capture import capture_output

    # The IPython display class for each built-in renderer's output. A custom
    # renderer uses the display class of its nearest built-in ancestor.
    _DISPLAY = {
        'markdown': Markdown,
        'latex': Latex,
        'html': HTML,
        'plain_text': Pretty,
        'base': Pretty,
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
    config.set_option('format_code', line)


def display_class_for(renderer_cls: type[BaseRenderer]) -> type:
    """The display class of the renderer's nearest built-in ancestor (or itself)."""
    for cls in renderer_cls.__mro__:
        name = cls.__dict__.get('name')
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
    config.set_option('jupyter_renderer', name)


@register_cell_magic
def render(line, cell):
    # Retrieve var dict from user namespace
    user_ns_prerun = ip.user_ns
    renderer_name = config.get_option('jupyter_renderer', config.DEFAULTS['jupyter_renderer'])
    renderer_cls = resolve_jupyter_renderer(renderer_name)
    display_class = display_class_for(renderer_cls)
    hc = HandCalcs(renderer=renderer_cls())
    # if line_args["sympy"]:
    #     cell = s_kit.convert_sympy_cell_to_py_cell(cell, user_ns_prerun)

    # Run the cell
    with cell_capture:
        exec_result = ip.run_cell(cell)

    if not exec_result.success:
        return None

    # Retrieve updated variables (after .run_cell(cell))
    user_ns_postrun = ip.user_ns

    # Do the handcalc conversion
    rendered = hc(cell, user_ns_postrun)

    # Display, but not as an "output"
    display(display_class(rendered))


def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, "cell")