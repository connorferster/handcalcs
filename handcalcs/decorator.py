__all__ = ["handcalc"]

from functools import wraps
import inspect
import innerscope
from handcalcs.handcalcs import LatexRenderer

def handcalc(left: str = "", right: str = "", jupyter_display: bool = False):
    # @wraps(func)
    def handcalc_decorator(func):
        # use innerscope to get the values of locals within the function
        scoped_func = innerscope.scoped_function(func)

        def wrapper(*args, **kwargs):
            func_source = inspect.getsource(func)
            cell_source = _func_source_to_cell(func_source)
            scope = scoped_func(*args, **kwargs)
            calculated_results = scope.inner_scope
            renderer = LatexRenderer(cell_source, calculated_results)
            latex_code = renderer.render()
            if jupyter_display:
                try:
                    from IPython.display import Latex, display
                except ModuleNotFoundError:
                    ModuleNotFoundError("jupyter_display option requires IPython.display to be installed.")
                display(Latex(latex_code))
                return calculated_results
            latex_code = latex_code.replace("\\[", "", 1).replace("\\]", "")
            return (left + latex_code + right, calculated_results)
        return wrapper
    return handcalc_decorator


def _func_source_to_cell(source: str):
    """
    Returns a string that represents `source` but with no signature, doc string,
    or return statement.
    
    `source` is a string representing a function's complete source code.
    """
    source_lines = source.split("\n")
    acc = []
    for line in source_lines:
        doc_string = False
        if not doc_string and '"""' in line:
            doc_string = True
            continue
        elif doc_string and '"""' in line:
            doc_string = False
            continue
        if (
            "def" not in line
            and not doc_string
            and "return" not in line
            and "@" not in line
        ):
            acc.append(line)
    return "\n".join(acc)
