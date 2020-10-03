__all__ = ["handcalc"]

from functools import wraps
import inspect
import innerscope
from handcalcs.handcalcs import LatexRenderer


def handcalc(
    override: str = "", precision: int = 3, left: str = "", right: str = "", decimal_separator:str = ".", jupyter_display: bool = False
):
    # @wraps(func)
    def handcalc_decorator(func):

        def wrapper(*args, **kwargs):
            line_args = {"override": override, "precision": precision}
            func_source = inspect.getsource(func)
            cell_source = _func_source_to_cell(func_source)
            # use innerscope to get the values of locals, closures, and globals when calling func
            scope = innerscope.call(func, *args, **kwargs)
            LatexRenderer.dec_sep = decimal_separator
            renderer = LatexRenderer(cell_source, scope, line_args)
            latex_code = renderer.render()
            if jupyter_display:
                try:
                    from IPython.display import Latex, display
                except ModuleNotFoundError:
                    ModuleNotFoundError(
                        "jupyter_display option requires IPython.display to be installed."
                    )
                display(Latex(latex_code))
                return scope.return_value

            # https://stackoverflow.com/questions/9943504/right-to-left-string-replace-in-python
            latex_code = "".join(latex_code.replace("\\[", "", 1).rsplit("\\]", 1))
            return (left + latex_code + right, scope.return_value)

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
    doc_string = False
    for line in source_lines:
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
