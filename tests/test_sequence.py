"""
Layer-1 tests for ``HcSequence`` (the root node) and the free helper
functions in ``parsing/sequence.py``: tree flattening, if-tree conversion,
level assignment, and the ``from_source`` factory.

The exhaustive nested-block shape produced by ``from_source`` is already
asserted by ``test_parser.py::test_hcsequence``; here we cover the smaller
units and invariants without duplicating that large fixture.
"""
from collections import deque

import pytest

from handcalcs.parsing.sequence import (
    HcSequence,
    flatten,
    flatten_deque,
    convert_if_tree,
    set_level,
)
from handcalcs.parsing.block_nodes import IfBlock, ElifBlock, ForBlock
from handcalcs.parsing.line_nodes import CalcLine
from handcalcs.parsing.nodes import Name, Constant


def test_flatten_recurses_nested_deques():
    nested = deque([1, deque([2, deque([3]), 4]), 5])
    assert list(flatten(nested)) == [1, 2, 3, 4, 5]


def test_flatten_deque_returns_deque():
    result = flatten_deque(deque([1, deque([2, 3])]))
    assert result == deque([1, 2, 3])
    assert isinstance(result, deque)


def test_convert_if_tree_wraps_ifblock_as_elifblock():
    ib = IfBlock(lines=deque([]), test=deque([]), orelse=deque([]))
    assert isinstance(convert_if_tree(ib), ElifBlock)


def test_convert_if_tree_passes_through_non_ifblock():
    fb = ForBlock(lines=deque([]))
    assert convert_if_tree(fb) is fb


def test_set_level_mutates_and_returns_node():
    cl = CalcLine(assigns=deque([Name("a")]), expression_tree=deque([Constant(1)]))
    returned = set_level(cl, 3)
    assert returned is cl
    assert cl.level == 3


def test_from_source_stores_globals_and_locals():
    seq = HcSequence.from_source("a = 1\n", {"a": 1}, {})
    assert seq.type == "root"
    assert seq.hc_globals == {"a": 1}
    assert seq.hc_locals == {}


def test_from_source_converts_top_level_if_to_elif_block():
    source = "a = 2\nif a > 1:\n    b = 3\n"
    seq = HcSequence.from_source(source, {"a": 2, "b": 3}, {})
    kinds = [type(node).__name__ for node in seq.sequence]
    assert kinds == ["CalcLine", "ElifBlock"]


def test_from_source_assigns_nesting_levels():
    source = "a = 2\nif a > 1:\n    b = 3\n"
    seq = HcSequence.from_source(source, {"a": 2, "b": 3}, {})
    elif_block = seq.sequence[-1]
    inner_if = elif_block.lines[0]
    # The CalcLine nested one block deep is at level 1.
    nested_calc = inner_if.lines[0]
    assert nested_calc.level == 1
