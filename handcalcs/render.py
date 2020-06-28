import sys
from . import handcalcs as hand

try: 
    from IPython.core.magic import (Magics, magics_class, cell_magic, register_cell_magic)
    from IPython import get_ipython
    from IPython.core.magics.namespace import NamespaceMagics
    from IPython.display import Latex, Markdown, display
    from IPython.utils.capture import capture_output
except ImportError:
    pass


try:
    _nms = NamespaceMagics()
    _Jupyter = get_ipython()
    _nms.shell = _Jupyter.kernel.shell
    cell_capture = capture_output(stdout=True, stderr=True, display=True)
except AttributeError:
    raise ImportError("handcalcs.render is intended for a Jupyter environment."
    " Use 'from handcalcs import handcalc' for the decorator interface.")

@register_cell_magic
def render(line, cell):
    # Run the cell
    with cell_capture:
        _nms.shell.run_cell(cell)

    # Retrieve variables from the local namespace
    var_list = _nms.who_ls()
    var_dict = {v: _nms.shell.user_ns[v] for v in var_list}
    renderer = hand.LatexRenderer(cell, var_dict)
    latex_code = renderer.render()
    display(Latex(latex_code))


@register_cell_magic
def tex(line, cell):
    # Run the cell
    _nms.shell.run_cell(cell)
    
    # Retrieve variables from the local namespace
    var_list = _nms.who_ls()
    var_dict = {v: _nms.shell.user_ns[v] for v in var_list}
    renderer = hand.LatexRenderer(cell, var_dict)
    latex_code = renderer.render()
    print(latex_code)

def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, 'cell')
