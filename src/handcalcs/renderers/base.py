from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional
from handcalcs.parsing.nodes import HcNode



@dataclass
class BaseRenderer:
    node_handlers: dict[str, Callable]
    symbolic_rules: list[Callable]
    numeric_rules: list[Callable]