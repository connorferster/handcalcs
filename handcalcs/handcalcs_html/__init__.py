import os
import os.path
import pathlib

from traitlets.config import Config
from nbconvert.exporters.html import HTMLExporter

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------

class MyExporter(HTMLExporter):
    """
    My custom exporter
    """

    # If this custom exporter should add an entry to the
    # "File -> Download as" menu in the notebook, give it a name here in the
    # `export_from_notebook` class member
    export_from_notebook = "handcalcs HTML"

    @property
    def template_paths(self):
        """
        We want to inherit from HTML template, and have template under
        ``./templates/`` so append it to the search path. (see next section)

        Note: nbconvert 6.0 changed ``template_path`` to ``template_paths``
        """
        nbconvert_templates = super().template_paths
        handcalcs_html_template = pathlib.Path(__file__) / "classic"
        nbconvert_templates.append(str(handcalcs_html_template))
        return nbconvert_templates

    def _template_file_default(self):
        """
        We want to use the new template we ship with our library.
        """
        return 'handcalcs_html' # full