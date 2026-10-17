"""
The ExcelRenderer: handcalcs source -> a live, formula-based Excel worksheet.

XlsxWriter is an optional dependency (``pip install handcalcs[excel]``). It is
imported only when a workbook is written, so this package (and the renderer
registry entry ``'excel'``) is always importable.
"""
from .compat import ExcelRendererIncompatibleError
from .renderer import ExcelRenderer
from .writer import ExcelWorkbook

__all__ = ["ExcelRenderer", "ExcelRendererIncompatibleError", "ExcelWorkbook"]
