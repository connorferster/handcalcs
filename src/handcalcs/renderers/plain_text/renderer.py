from dataclasses import dataclass
from .base import BaseRenderer
from ..parsing.nodes import Name

@dataclass
class PlainTextRenderer(BaseRenderer):
    pass
