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

from nbconvert import PDFExporter, HTMLExporter, LatexExporter


class HTMLHideInputExporter(HTMLExporter):
    """
    Exports HTML documents without input cells.
    """

    export_from_notebook = "HTML Hide Input"
    exclude_input = HTMLExporter.exclude_input
    exclude_input.default_value = True


class PDFHideInputExporter(PDFExporter):
    """
    Exports PDF documents without input cells.
    """

    export_from_notebook = "PDF Hide Input"
    exclude_input = PDFExporter.exclude_input
    exclude_input.default_value = True


class LatexHideInputExporter(LatexExporter):
    """
    Exports LaTeX documents without input cells.
    """

    export_from_notebook = "LaTeX Hide Input"
    exclude_input = LatexExporter.exclude_input
    exclude_input.default_value = True