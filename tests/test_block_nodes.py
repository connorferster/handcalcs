"""
Layer-1 data-model tests for block nodes, focused on the branching
``ElifBlock.from_if_tree`` flattening logic.
"""
from collections import deque

import pytest

from handcalcs.parsing.nodes import Name, Constant
from handcalcs.parsing.line_nodes import CalcLine
from handcalcs.parsing.block_nodes import (
    FunctionBlock,
    ForBlock,
    IfBlock,
    ElseBlock,
    ElifBlock,
)


def _calc(identifier, value):
    return CalcLine(
        assigns=deque([Name(identifier)]), expression_tree=deque([Constant(value)])
    )


def test_block_defaults():
    assert FunctionBlock().type == "function_block"
    assert FunctionBlock().level == 0
    assert ForBlock().type == "for_block"
    assert IfBlock().type == "if_block"
    assert IfBlock().is_true is None
    assert ElseBlock().type == "else_block"
    assert ElifBlock().type == "elif_block"


# --- ElifBlock.from_if_tree ---------------------------------------------

def test_from_if_tree_single_if_no_orelse():
    ib = IfBlock(
        lines=deque([_calc("d", 4)]),
        test=deque([Name("a"), ">", Constant(2)]),
        orelse=deque([]),
    )
    eb = ElifBlock.from_if_tree(ib)
    assert isinstance(eb, ElifBlock)
    assert [type(x).__name__ for x in eb.lines] == ["IfBlock"]


def test_from_if_tree_if_else_appends_else_block():
    ib = IfBlock(
        lines=deque([_calc("d", 4)]),
        test=deque([Name("a"), ">", Constant(2)]),
        orelse=deque([_calc("d", 6)]),
    )
    eb = ElifBlock.from_if_tree(ib)
    assert [type(x).__name__ for x in eb.lines] == ["IfBlock", "ElseBlock"]


def test_from_if_tree_nested_elif_flattens():
    # if / elif / else, expressed as a nested-orelse IfBlock tree.
    inner = IfBlock(
        lines=deque([_calc("d", 5)]),
        test=deque([Name("a"), ">", Name("b")]),
        orelse=deque([_calc("d", 6)]),
    )
    outer = IfBlock(
        lines=deque([_calc("d", 4)]),
        test=deque([Constant(2), "<=", Name("a"), "<", Constant(5)]),
        orelse=deque([inner]),
    )
    eb = ElifBlock.from_if_tree(outer)
    # Two IfBlock clauses (if + elif) plus a trailing ElseBlock.
    assert [type(x).__name__ for x in eb.lines] == ["IfBlock", "IfBlock", "ElseBlock"]
