"""
Layer-1 data-model tests for the primitive nodes in ``parsing/nodes.py``:
field defaults, the ``type`` discriminant, equality, and the base
``HcNode.render`` contract.
"""
from collections import deque

import pytest

from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
    Attribute,
    List,
    Tuple,
    Set,
    Dictionary,
)
from handcalcs.parsing.null_values import NoValue


def test_hcnode_render_not_implemented():
    with pytest.raises(NotImplementedError):
        HcNode().render()


def test_name_defaults():
    n = Name("alpha")
    assert n.identifier == "alpha"
    assert n.value == NoValue()
    assert n.type == "name"


def test_name_with_value():
    assert Name("alpha", 3).value == 3


def test_constant_requires_value_and_has_type():
    c = Constant(4)
    assert c.value == 4
    assert c.type == "constant"


def test_attribute_defaults():
    a = Attribute("obj", "attr")
    assert a.namespace == "obj"
    assert a.identifier == "attr"
    assert a.value == NoValue()
    assert a.type == "attribute"


@pytest.mark.parametrize(
    "cls,type_str",
    [(List, "list"), (Tuple, "tuple"), (Set, "set")],
    ids=["list", "tuple", "set"],
)
def test_sequence_collection_nodes(cls, type_str):
    node = cls(deque([Constant(1), Constant(2)]))
    assert node.elems == deque([Constant(1), Constant(2)])
    assert node.type == type_str


def test_dictionary_node():
    d = Dictionary(deque([Constant(1)]), deque([Constant(2)]))
    assert d.keys == deque([Constant(1)])
    assert d.values == deque([Constant(2)])
    assert d.type == "dictionary"


def test_node_equality_is_structural():
    assert Name("a", 1) == Name("a", 1)
    assert Name("a", 1) != Name("a", 2)
    assert Constant(1) != Name("a", 1)
