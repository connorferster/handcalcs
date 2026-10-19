from __future__ import annotations

from typing import ClassVar

from handcalcs.renderers.base import BaseRenderContext, BaseRenderer, RenderContext
from . import omml


class WordRenderer(BaseRenderer):
    """
    Renders a HandCalcs sequence as a Word document (.docx) whose calculations
    are native, editable Word equations (Office Math Markup, OMML).

    Like the LaTeX renderer, the node handlers return math as strings, here OMML
    fragments (see ``omml``), and the base renderer's line and block machinery
    works on them unchanged. Only building the document parses XML, so
    python-docx (``pip install handcalcs[word]``) is imported only then.
    """

    name = "word"

    # A continuation row (a source line continuation) starts with an em space.
    CONTINUATION_INDENT: ClassVar[str] = omml.run(omml.EM_SPACE)
    # Collections longer than MAX_ITEMS show only their first and last
    # EDGE_ITEMS items (an equation row cannot break).
    MAX_ITEMS: ClassVar[int] = 10
    EDGE_ITEMS: ClassVar[int] = 3

    def create_context(self, **kwargs) -> BaseRenderContext:
        # Word spaces math itself, so the base handlers join components with no
        # space; brackets are the two halves of a growing ``m:d`` delimiter.
        return BaseRenderContext(
            global_context=RenderContext(
                space="",
                newline="\n",
                indent="",
                lpar=omml.delim_open(),
                rpar=omml.DELIM_CLOSE,
                **kwargs,
            ),
            line_context=RenderContext.sparse(),
        )

    def leading_sign(self, rendered: str) -> bool:
        return omml.plain_text(rendered).lstrip().startswith(("-", "+", "−"))
