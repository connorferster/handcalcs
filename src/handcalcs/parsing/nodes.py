from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from .null_values import NoValue


@dataclass
class HcNode:
    pass
    # type: str

    def render(self):
        raise NotImplementedError(
            f"The render method for {__class__.__name__} has not been implemented yet."
        )


@dataclass
class Name(HcNode):
    identifier: str
    value: Any = NoValue()
    type: str = "name"


@dataclass
class Constant(HcNode):
    """
    A scalar value: a literal from the source (``calculated=False``, with its
    text as written in ``source_text``) or a value computed at runtime and shown
    in a substitution or result (``calculated=True``).
    """

    value: Any
    source_text: str = field(default="", compare=False)
    calculated: bool = False
    type: str = "constant"


@dataclass
class Attribute(HcNode):
    """
    An attribute: of a dotted name (``math.pi``, ``beam.length``; ``namespace``
    is the dotted name) or of an expression (``(L * 2).magnitude``; then
    ``namespace`` is empty and ``receiver`` is the expression's node).
    """

    namespace: str
    identifier: str
    value: Any = NoValue()
    receiver: Any = None
    type: str = "attribute"


@dataclass
class List(HcNode):
    elems: deque[Any]
    type: str = "list"


@dataclass
class Tuple(HcNode):
    """
    A tuple. ``bare`` is True for the targets of an assignment or a loop
    (``a, b = 1, 2``), which are shown without brackets.
    """

    elems: deque[Any]
    bare: bool = False
    type: str = "tuple"


@dataclass
class Set(HcNode):
    elems: deque[Any]
    type: str = "set"


@dataclass
class Dictionary(HcNode):
    keys: deque[Any]
    values: deque[Any]
    type: str = "dictionary"


@dataclass
class Matrix(HcNode):
    """A two-dimensional array (a numpy array's value): ``rows`` of element nodes."""

    rows: deque[deque[Any]]
    type: str = "matrix"


@dataclass
class Subscript(HcNode):
    """
    An index or key lookup: ``xs[0]``, ``loads["dead"]``, ``A[i, j]``. ``index``
    holds one node per dimension (a ``Slice`` for ``a:b``).

    ``labels`` is set when the container is a name and every index is an
    integer, a short string or a name: the text of each index and whether it is
    a name, so that a renderer can show the index as a subscript of the name
    (``xs[0]`` -> xs with subscript 0). Otherwise it is None.

    ``value`` is the element, looked up without evaluating code (see
    ``AstParser._subscript_value``), or NoValue.
    """

    container: Any
    index: deque[Any]
    labels: Optional[list[tuple[str, bool]]] = None
    value: Any = NoValue()
    type: str = "subscript"


@dataclass
class Slice(HcNode):
    """A slice in a subscript, ``a:b`` or ``a:b:c``; a missing part is None."""

    lower: Any = None
    upper: Any = None
    step: Any = None
    type: str = "slice"
