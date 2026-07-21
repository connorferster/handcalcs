# __all__ = ["handcalc"]

# from typing import Optional, Callable
# from functools import wraps, update_wrapper
# import inspect
# import innerscope
# from .handcalcs import LatexRenderer


# def handcalc(
#     override: str = "",
#     precision: int = 3,
#     left: str = "",
#     right: str = "",
#     scientific_notation: Optional[bool] = None,
#     jupyter_display: bool = False,
#     record: bool = False,
# ):
#     def handcalc_decorator(func):
#         if record:
#             decorated = HandcalcsCallRecorder(
#                 func,
#                 override,
#                 precision,
#                 left,
#                 right,
#                 scientific_notation,
#                 jupyter_display,
#             )
#         else:

#             @wraps(func)
#             def decorated(*args, **kwargs):
#                 line_args = {
#                     "override": override,
#                     "precision": precision,
#                     "sci_not": scientific_notation,
#                 }
#                 func_source = inspect.getsource(func)
#                 cell_source = _func_source_to_cell(func_source)
#                 # innerscope retrieves values of locals, closures, and globals
#                 scope = innerscope.call(func, *args, **kwargs)
#                 renderer = LatexRenderer(cell_source, scope, line_args)
#                 latex_code = renderer.render()
#                 raw_latex_code = "".join(
#                     latex_code.replace("\\[", "", 1).rsplit("\\]", 1)
#                 )
#                 if jupyter_display:
#                     try:
#                         from IPython.display import Latex, display
#                     except ModuleNotFoundError:
#                         ModuleNotFoundError(
#                             "jupyter_display option requires IPython.display to be installed."
#                         )
#                     display(Latex(latex_code))
#                     return scope.return_value
#                 return (left + raw_latex_code + right, scope.return_value)

#         return decorated

#     return handcalc_decorator


# class HandcalcsCallRecorder:
#     """
#     Records function calls for the func stored in .callable
#     """

#     def __init__(
#         self,
#         func: Callable,
#         _override: str = "",
#         _precision: int = 3,
#         _left: str = "",
#         _right: str = "",
#         _scientific_notation: Optional[bool] = None,
#         _jupyter_display: bool = False,
#     ):
#         self.callable = func
#         self.history = list()
#         self._override = _override
#         self._precision = _precision
#         self._left = _left
#         self._right = _right
#         self._scientific_notation = _scientific_notation
#         self._jupyter_display = _jupyter_display
#         update_wrapper(self, func)

#     def __repr__(self):
#         return f"{self.__class__.__name__}({self.callable.__name__}, num_of_calls: {len(self.history)})"

#     @property
#     def calls(self):
#         return len(self.history)

#     def __call__(self, *args, **kwargs):
#         line_args = {
#             "override": self._override,
#             "precision": self._precision,
#             "sci_not": self._scientific_notation,
#         }
#         func_source = inspect.getsource(self.callable)
#         cell_source = _func_source_to_cell(func_source)
#         # innerscope retrieves values of locals, closures, and globals
#         scope = innerscope.call(self.callable, *args, **kwargs)
#         renderer = LatexRenderer(cell_source, scope, line_args)
#         latex_code = renderer.render()
#         raw_latex_code = "".join(latex_code.replace("\\[", "", 1).rsplit("\\]", 1))
#         self.history.append({"return": scope.return_value, "latex": raw_latex_code})
#         if self._jupyter_display:
#             try:
#                 from IPython.display import Latex, display
#             except ModuleNotFoundError:
#                 ModuleNotFoundError(
#                     "jupyter_display option requires IPython.display to be installed."
#                 )
#             display(Latex(latex_code))
#             return scope.return_value
#         return (self._left + raw_latex_code + self._right, scope.return_value)


# def _func_source_to_cell(source: str):
#     """
#     Returns a string that represents `source` but with no signature, doc string,
#     or return statement.

#     `source` is a string representing a function's complete source code.
#     """
#     source_lines = source.split("\n")
#     acc = []
#     doc_string = False
#     for line in source_lines:
#         if (
#             not doc_string
#             and line.lstrip(" \t").startswith('"""')
#             and line.lstrip(" \t").rstrip().endswith('"""', 3)
#         ):
#             doc_string = False
#             continue
#         elif (
#             not doc_string
#             and line.lstrip(" \t").startswith('"""')
#             and not line.lstrip(" \t").rstrip().endswith('"""', 3)
#         ):
#             doc_string = True
#             continue
#         elif doc_string and '"""' in line:
#             doc_string = False
#             continue
#         if (
#             "def" not in line
#             and not doc_string
#             and "return" not in line
#             and "@" not in line
#         ):
#             acc.append(line)
#     return "\n".join(acc)
