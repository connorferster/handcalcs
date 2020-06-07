from . import handcalcs as hand
from . import numpy_and_pandas_patches as patches
from IPython.core.magic import (Magics, magics_class, cell_magic, register_cell_magic)
from IPython import get_ipython
from IPython.core.magics.namespace import NamespaceMagics
from IPython.display import Latex, Markdown, display
from IPython.utils.capture import capture_output
import sys

_nms = NamespaceMagics()
_Jupyter = get_ipython()
_nms.shell = _Jupyter.kernel.shell

cell_capture = capture_output(stdout=True, stderr=True, display=True)

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

@register_cell_magic
def tester(line, cell):
    print(str(type(_Jupyter)))
    print("incl. forallpeople? \n", any(["forallpeople" in module for module in sys.modules]))
    print("incl. pandas? ", any(["pandas" in module for module in sys.modules]))
    print(sys.modules["pandas"])
    #print("Jupyter.system: \n", _Jupyter.system())
    #print("Jupyter.system_piped: \n", _Jupyter.system_piped())

def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, 'cell')
    # pandas_loaded = any(["pandas" in module for module in sys.modules])
    # numpy_loaded = any(["numpy" in module for module in sys.modules])
    # # TODO: Apparently pandas_loaded can register as True even without pandas loaded
    try:
        pandas_module = sys.modules["pandas"]
        pandas_module.DataFrame.hc_latex = patches.dataframe_repr_latex
        pandas_module.Series.hc_latex = patches.series_repr_latex
        print("Ran")
    except:
        pass
    
    try: 
        numpy_module = sys.modules["numpy"]
        numpy_module.matrix.hc_latex = patches.numpy_repr_latex
        #numpy_module.ndarray.hc_latex = patches.numpy_repr_latex
        print("Ran")
    except:
        pass

    # if numpy_loaded:
    #     pass
        