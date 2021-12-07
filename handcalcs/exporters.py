from copy import copy

from nbconvert import PDFExporter, HTMLExporter, LatexExporter


class HTMLHideInputExporter(HTMLExporter):
    """
    Exports HTML documents without input cells.
    """

    export_from_notebook = "HTML Hide Input"
    exclude_input = copy(HTMLExporter.exclude_input)
    exclude_input.default_value = True


class PDFHideInputExporter(PDFExporter):
    """
    Exports PDF documents without input cells.
    """

    export_from_notebook = "PDF Hide Input"
    exclude_input = copy(PDFExporter.exclude_input)
    exclude_input.default_value = True


class LatexHideInputExporter(LatexExporter):
    """
    Exports LaTeX documents without input cells.
    """

    export_from_notebook = "LaTeX Hide Input"
    exclude_input = copy(LatexExporter.exclude_input)
    exclude_input.default_value = True
