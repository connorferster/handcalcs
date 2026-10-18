"""
Layer-1 data-model tests for inline nodes, including the branching
``InlineCommand.from_raw_comment`` constructor.
"""
from collections import deque

import pytest

from handcalcs.parsing.nodes import Name, Constant
from handcalcs.parsing.operator_nodes import GtOp
from handcalcs.parsing.commands import CommentCommandError
from handcalcs.parsing.inline_nodes import (
    FunctionCall,
    Compare,
    InlineComment,
    InlineCommand,
    Comprehension,
    ComprehensionChain,
)


def test_function_call_defaults():
    fc = FunctionCall()
    assert fc.namespace == deque()
    assert fc.function_name == deque()
    assert fc.args == deque()
    assert fc.type == "function_call"


def test_compare_holds_comparison_deque():
    c = Compare(deque([Name("a"), GtOp, Constant(2)]))
    assert c.type == "compare"
    assert len(c.comparison) == 3


def test_inline_comment_node():
    ic = InlineComment("a note")
    assert ic.content == "a note"
    assert ic.type == "inline_comment"


def test_comprehension_and_chain_defaults():
    comp = Comprehension(
        assigns=deque([Name("elem")]),
        iterator=deque([Name("a")]),
        is_async=False,
    )
    assert comp.type == "comprehension"
    assert comp.is_async is False

    chain = ComprehensionChain(comp_type="list")
    assert chain.type == "comprehension_chain"
    assert chain.comp_type == "list"
    assert chain.comprehensions == deque()


# --- InlineCommand.from_raw_comment: three code paths --------------------

def test_from_raw_comment_non_command_returns_inline_comment():
    result = InlineCommand.from_raw_comment("an inline note")
    assert isinstance(result, InlineComment)
    assert result.content == "an inline note"


def test_from_raw_comment_kwarg_style():
    result = InlineCommand.from_raw_comment("hc: precision=3")
    assert isinstance(result, InlineCommand)
    assert result.commands == {"precision": 3}


def test_from_raw_comment_flag_style_falls_back_to_argparse():
    result = InlineCommand.from_raw_comment("hc: -f 5E")
    assert isinstance(result, InlineCommand)
    assert result.commands["format_code"] == "5E"
    # argparse defaults are present alongside the parsed flag.
    assert result.commands["multiline"] is False
    assert result.commands["ignore"] is False


def test_from_raw_comment_unknown_flag_raises_not_exits():
    # argparse would sys.exit(2); a typo in a comment must not end the program.
    with pytest.raises(CommentCommandError, match=r"'# hc: --mdoe no_num'"):
        InlineCommand.from_raw_comment("hc: --mdoe no_num")


def test_from_raw_comment_invalid_value_raises():
    with pytest.raises(CommentCommandError, match="invalid int value: 'two'"):
        InlineCommand.from_raw_comment("hc: -c two")
