__all__ = ["handcalc"]

from typing import Optional, Callable
from functools import wraps
import inspect
import innerscope
from .handcalcs import LatexRenderer


def handcalc(
    override: str = "",
    precision: int = 3,
    left: str = "",
    right: str = "",
    scientific_notation: Optional[bool] = None,
    jupyter_display: bool = False,
    record: bool = False,
):
    def handcalc_decorator(func):
        if record:
            class CallRecorder:
                """
                Records function calls for the func stored in .callable
                """
                def __init__(self, func: Callable):
                    self.callable = func
                    self.history = list()

                def __repr__(self):
                    return f"FunctionRecorder({self.callable.__name__}, num_of_calls: {len(self.history)})"

                @property
                def calls(self):
                    return len(self.history)


                @wraps(func)
                def __call__(self, *args, **kwargs):
                    line_args = {
                        "override": override,
                        "precision": precision,
                        "sci_not": scientific_notation,
                    }
                    func_source = inspect.getsource(func)
                    cell_source = _func_source_to_cell(func_source)
                    # innerscope retrieves values of locals, closures, and globals
                    scope = innerscope.call(func, *args, **kwargs)
                    renderer = LatexRenderer(cell_source, scope, line_args)
                    latex_code = renderer.render()
                    raw_latex_code = "".join(latex_code.replace("\\[", "", 1).rsplit("\\]", 1))
                    self.history.append({"return": scope.return_value, "latex": raw_latex_code})
                    if jupyter_display:
                        try:
                            from IPython.display import Latex, display
                        except ModuleNotFoundError:
                            ModuleNotFoundError(
                                "jupyter_display option requires IPython.display to be installed."
                            )
                        display(Latex(latex_code))
                        return scope.return_value
                    return (left + raw_latex_code + right, scope.return_value)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                line_args = {
                    "override": override,
                    "precision": precision,
                    "sci_not": scientific_notation,
                }
                func_source = inspect.getsource(func)
                cell_source = _func_source_to_cell(func_source)
                # innerscope retrieves values of locals, closures, and globals
                scope = innerscope.call(func, *args, **kwargs)
                renderer = LatexRenderer(cell_source, scope, line_args)
                latex_code = renderer.render()
                raw_latex_code = "".join(latex_code.replace("\\[\n", "", 1).rsplit("\\]\n", 1))
                if jupyter_display:
                    try:
                        from IPython.display import Latex, display
                    except ModuleNotFoundError:
                        ModuleNotFoundError(
                            "jupyter_display option requires IPython.display to be installed."
                        )
                    display(Latex(latex_code))
                    return scope.return_value
                return (left + raw_latex_code + right, scope.return_value)
        if record:
            return CallRecorder(func)
        else:
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
        if (
            not doc_string
            and line.lstrip(" \t").startswith('"""')
            and line.lstrip(" \t").rstrip().endswith('"""', 3)
        ):
            doc_string = False
            continue
        elif (
            not doc_string
            and line.lstrip(" \t").startswith('"""')
            and not line.lstrip(" \t").rstrip().endswith('"""', 3)
        ):
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
