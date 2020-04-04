import handcalcs as hand
from IPython.core.magic import (Magics, magics_class, cell_magic, register_cell_magic)
from IPython import get_ipython
from IPython.core.magics.namespace import NamespaceMagics
from IPython.display import Latex, Markdown
_nms = NamespaceMagics()
_Jupyter = get_ipython()
_nms.shell = _Jupyter.kernel.shell

import inspect

@register_cell_magic
def render(line, cell):
    # Run the cell
    _nms.shell.run_cell(cell)
    
    # Retrieve variables from the local namespace
    var_list = _nms.who_ls()
    var_dict = {v: _nms.shell.user_ns[v] for v in var_list}
    renderer = hand.LatexRenderer(cell, var_dict)
    latex_code = renderer.render()
    #print(latex_code)
    display(Latex(latex_code))


def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, 'cell')
