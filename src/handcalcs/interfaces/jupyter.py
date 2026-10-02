import sys
from string import Formatter
from .object_oriented import HandCalcs
from handcalcs import config
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.plaintext import PlainTextRenderer

_RENDERERS = {
    "latex": LatexRenderer,
    "html": HTMLRenderer,
    "plain_text": PlainTextRenderer,
}

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

    _DISPLAY = {
        'latex': Latex,
        'html': HTML,
        'plain_text': Pretty
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


@register_line_magic
def hc_default_renderer(line):
    if line not in ('latex', 'html', 'plain_text'):
        raise ValueError(
            f"The argument must be one of ('latex', 'html', 'plain_text'), not: {line}"
        )
    config.set_option('default_renderer', line)


@register_cell_magic
def render(line, cell):
    # Retrieve var dict from user namespace
    user_ns_prerun = ip.user_ns
    hc_config = config.get_config()
    renderer_name = hc_config.get('default_renderer', '')
    config_renderer = _RENDERERS.get(renderer_name, None)
    if config_renderer is None:
        raise ValueError(
            f"Renderer name of '{renderer_name}' has not been implemented. "
            "Try one of ('latex', 'html', 'plain_text')."
        )
    display_class = _DISPLAY[renderer_name]

    hc = HandCalcs(renderer=config_renderer())
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