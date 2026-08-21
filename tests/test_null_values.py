"""
Layer-1 tests for the sentinel value nodes in ``parsing/null_values.py``.
"""
import pytest

from handcalcs.parsing.null_values import NoValue, HcNotImplemented


def test_novalue_type_and_render():
    nv = NoValue()
    assert nv.type == "no_value"
    assert nv.render() == ""


def test_novalue_equality_between_instances():
    assert NoValue() == NoValue()


def test_novalue_not_equal_to_other_types():
    assert (NoValue() == 5) is False
    assert (NoValue() == "no_value") is False


def test_novalue_ne_operator_behaves():
    # NoValue defines a (misspelled, never-called) `__neq__`, but `!=` is
    # correctly derived by Python from `__eq__`, so these hold regardless.
    assert (NoValue() != NoValue()) is False
    assert (NoValue() != 5) is True


def test_novalue_is_frozen_and_hashable():
    nv = NoValue()
    with pytest.raises(Exception):
        nv.type = "changed"  # frozen dataclass
    assert isinstance(hash(nv), int)


def test_hcnotimplemented_carries_node_name():
    ni = HcNotImplemented(node_name="SomeNode")
    assert ni.node_name == "SomeNode"
    assert ni.type == "not_implemented"
