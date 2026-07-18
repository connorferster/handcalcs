from dataclasses import dataclass, field
from typing import Optional
from handcalcs.renders.base import BaseRenderer, RenderContext

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    
)

@dataclass
class PlainTextRenderContext(RenderContext):
    mode: Optional[str] = None
    commands: Optional[dict] = None


class PlainTextRenderer(BaseRenderer):
    name = 'plain_text'

    def create_context(
        self, 
        node: Optional[HcNode] = None, 
        mode: Optional[str] = None,
        commands: Optional[dict] = None
        ):
        context = PlainTextRenderContext(mode, commands)
        return context

@PlainTextRenderer.register('name')
def render_name(renderer: PlainTextRenderer, node: )

            

