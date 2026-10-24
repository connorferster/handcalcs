"""
The error raised for Python that cannot become a live Excel worksheet.

The renderer raises ``ExcelRendererIncompatibleError`` *during render*, before
any workbook is written, so an incompatible cell never produces a partial or
silently wrong sheet.
"""

from __future__ import annotations
from typing import Any, Optional


class ExcelRendererIncompatibleError(Exception):
    """
    Raised when a handcalcs node has no faithful Excel representation, e.g. a
    for loop, a ``print()`` call, an import of a module other than ``math``, a
    list, or a function with no Excel equivalent.

    ``reason`` is a short human-readable explanation; ``node`` is the offending
    node (when there is one) and ``target`` is the variable whose assignment was
    being rendered (when known).
    """

    def __init__(self, reason: str, node: Any = None, target: Optional[str] = None):
        self.reason = reason
        self.node = node
        self.target = target
        super().__init__(self._message())

    @property
    def node_type(self) -> Optional[str]:
        if self.node is None:
            return None
        return getattr(self.node, "type", type(self.node).__name__)

    def _message(self) -> str:
        message = f"Cannot render to Excel: {self.reason}"
        if self.target is not None:
            message += f" (in the assignment to '{self.target}')"
        return message

    def with_target(self, target: str) -> "ExcelRendererIncompatibleError":
        """Return the same error annotated with the assignment target."""
        if self.target is not None:
            return self
        return ExcelRendererIncompatibleError(self.reason, self.node, target)


def incompatible(reason: str, node: Any = None) -> ExcelRendererIncompatibleError:
    """Shorthand used by the handlers: ``raise incompatible("...", node)``."""
    return ExcelRendererIncompatibleError(reason, node)
