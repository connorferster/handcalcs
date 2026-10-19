"""
The WordRenderer: handcalcs source -> a .docx whose calculations are native,
editable Word equations (OMML).

python-docx is an optional dependency (``pip install handcalcs[word]``). It is
imported only when a document is built, so this package (and the renderer
registry entry ``'word'``) is always importable.
"""

from .renderer import WordRenderer
from . import handlers  # registers the node handlers on WordRenderer

__all__ = ["WordRenderer"]
