from collections import deque
from dataclasses import dataclass
from typing import Any


# Six basic line types
@dataclass
class CalcLine:
    assigns: deque
    expression_tree: deque
    symbolic: deque
    numeric: deque
    result: Any
    comment: str
    latex: str


@dataclass
class IntertextLine:
    line: deque
    comment: str
    latex: str
    # TODO: Fill this in correctly based on historic