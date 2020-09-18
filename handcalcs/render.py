#    Copyright 2020 Connor Ferster

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import sys
from . import handcalcs as hand
from . import sympy_kit as s_kit

try: 
    from IPython.core.magic import (Magics, magics_class, cell_magic, register_cell_magic)
    from IPython import get_ipython
# from IPython.core.magics.namespace import NamespaceMagics
    from IPython.display import Latex, Markdown, display
    from IPython.utils.capture import capture_output
except ImportError:
    pass


try:
    ip = get_ipython()
    cell_capture = capture_output(stdout=True, stderr=True, display=True)
except AttributeError:
    raise ImportError("handcalcs.render is intended for a Jupyter environment."
    " Use 'from handcalcs import handcalc' for the decorator interface.")

def parse_line_args(line: str) -> dict:
    """
    Returns a dict that represents the validated arguments
    passed in as a line on the %%render or %%tex cell magics.
    """
    valid_args = ["params", "long", "short", "symbolic", "sympy", "_testing"]
    line_parts = line.split()
    parsed_args = {"override": "", "precision": ""}
    precision = ""
    for arg in line_parts:
        for valid_arg in valid_args:
            if arg.lower() in valid_arg: 
                parsed_args.update({"override": valid_arg})
                break
        try:
            precision = int(arg)
        except ValueError:
            pass
        if precision:
            parsed_args.update({"precision": precision})
    return parsed_args


@register_cell_magic
def render(line, cell):
    # Retrieve var dict from user namespace
    user_ns_prerun = ip.user_ns
    line_args = parse_line_args(line)

    if line_args["override"] == "sympy":
        cell = s_kit.convert_sympy_cell_to_py_cell(cell, user_ns_prerun)
    
    # Run the cell
    with cell_capture:
        ip.run_cell(cell)

    # Retrieve updated variables (after .run_cell(cell))
    user_ns_postrun = ip.user_ns

    # Do the handcalc conversion
    renderer = hand.LatexRenderer(cell, user_ns_postrun, line_args)
    latex_code = renderer.render()

    # Display, but not as an "output"
    display(Latex(latex_code))

    if line_args["override"] == "_testing":
        return latex_code


@register_cell_magic
def tex(line, cell):
    # Retrieve var dict from user namespace
    user_ns_prerun = ip.user_ns
    line_args = parse_line_args(line)

    if line_args["override"] == "sympy":
        cell = s_kit.convert_sympy_cell_to_py_cell(cell, user_ns_prerun)
    
    # Run the cell
    with cell_capture:
        ip.run_cell(cell)

    # Retrieve updated variables (after .run_cell(cell))
    user_ns_postrun = ip.user_ns

    # Do the handcalc conversion
    renderer = hand.LatexRenderer(cell, user_ns_postrun, line_args)
    latex_code = renderer.render()

    # Print Latex Code
    print(latex_code)

    if line_args["override"] == "_testing":
        return latex_code

def load_ipython_extension(ipython):
    """This function is called when the extension is
    loaded. It accepts an IPython InteractiveShell
    instance. We can register the magic with the
    `register_magic_function` method of the shell
    instance."""
    ipython.register_magic_function(render, 'cell')

# def unload_ipython_extension(ipython):
#     """This function is called when the extension is
#     loaded. It accepts an IPython InteractiveShell
#     instance. We can register the magic with the
#     `register_magic_function` method of the shell
#     instance."""
#     print(dir(ipython.magics_manager))
#     ipython.magics_manager.remove(render)
