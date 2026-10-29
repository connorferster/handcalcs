"""An HTML renderer that saves a '.pdf' destination as a PDF, through WeasyPrint."""
import pathlib

from weasyprint import CSS, HTML

from handcalcs.renderers import HTMLRenderer

# WeasyPrint does not break pages inside a flex layout, which the HTML output uses to
# stack its lines, so lay the lines out as blocks with the same spacing.
PRINT_CSS = CSS(string="""
    @page { size: A4; margin: 20mm; }
    .handcalcs, .handcalcs .hc-block, .handcalcs .hc-body { display: block !important; }
    .handcalcs :is(.handcalcs, .hc-block, .hc-body) > * + * { margin-top: var(--hc-gap); }
""")


class PDFRenderer(HTMLRenderer):
    """HTML output that is written as a PDF when the file name ends in '.pdf'."""

    def to_file(self, rendered, path):
        path = pathlib.Path(path)
        if path.suffix.lower() != ".pdf":
            return super().to_file(rendered, path)
        page = self.preamble + rendered + self.postamble
        HTML(string=page).write_pdf(path, stylesheets=[PRINT_CSS])
        return path
