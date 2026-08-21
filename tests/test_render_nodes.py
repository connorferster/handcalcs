"""
Representative Layer-3 tests: render individual nodes through a bare
``BaseRenderer`` and assert the produced string.

This module demonstrates the parametrized pattern the full per-node matrix
will follow (constants, names, collections, operators, comparisons, function
calls, comments). Known bugs are pinned with ``xfail(strict=True)`` per the
agreed policy so the suite documents them and flags a fix via an unexpected
pass.
"""
from collections import deque

import pytest

from handcalcs.renderers.base import ContextKeyError, ContextValueError
from handcalcs.parsing.nodes import Name, Constant, List, Tuple, Set, Dictionary
from handcalcs.parsing.operator_nodes import (
    AddOp,
    SubOp,
    MultOp,
    DivOp,
    PowOp,
    FloorOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    EqOp,
    NeqOp,
)
from handcalcs.parsing.inline_nodes import (
    FunctionCall,
    Compare,
    InlineComment,
    InlineCommand,
)
from handcalcs.parsing.line_nodes import (
    MarkdownComment,
    CalcLine,
    ExprLine,
    Import,
    CommentLine,
    CommentCommand,
)
from handcalcs.parsing.block_nodes import IfBlock, ElseBlock, ElifBlock


# ---------------------------------------------------------------------------
# Constant
# ---------------------------------------------------------------------------

def test_constant_applies_format_code(render):
    assert render(Constant(3.14159265), format_code=".3g") == "3.14"


def test_constant_int(render):
    assert render(Constant(4)) == "4"


def test_constant_non_numeric_falls_back_to_str(render):
    # A format code that does not apply to the value raises ValueError inside
    # the handler and falls back to plain str().
    assert render(Constant("foo")) == "foo"


# ---------------------------------------------------------------------------
# Name
# ---------------------------------------------------------------------------

def test_name_symbolic_mode_renders_identifier(render):
    assert render(Name("alpha", 3), current_mode="sym") == "alpha"


def test_name_numeric_mode_renders_formatted_value(render):
    assert render(Name("alpha", 3), current_mode="num") == "3"


def test_name_numeric_mode_applies_format_code(render):
    assert render(Name("alpha", 3.14159), current_mode="num", format_code=".2f") == "3.14"


def test_name_without_current_mode_raises(render):
    with pytest.raises(ContextKeyError):
        render(Name("a", 1))


def test_name_unknown_mode_raises(render):
    with pytest.raises(ContextValueError):
        render(Name("a", 1), current_mode="bogus")


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "node,expected",
    [
        (List(deque([Constant(1), Constant(2)])), "[1, 2]"),
        (List(deque([])), "[]"),
        (Set(deque([Constant(1)])), "{1}"),
        (Tuple(deque([Constant(1), Constant(2)])), "(1, 2)"),
        (Dictionary(deque([Constant(1)]), deque([Constant(2)])), "{1: 2}"),
    ],
    ids=["list", "empty-list", "set", "tuple", "dict"],
)
def test_collection_rendering(render, node, expected):
    assert render(node) == expected


# ---------------------------------------------------------------------------
# Binary operators
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "node,expected",
    [
        (AddOp(left=Constant(1), right=Constant(2)), "1+2"),
        (SubOp(left=Constant(1), right=Constant(2)), "1-2"),
        (MultOp(left=Constant(1), right=Constant(2)), "1*2"),
        (DivOp(left=Constant(1), right=Constant(2)), "1/2"),
        (PowOp(left=Constant(1), right=Constant(2)), "1**2"),
    ],
    ids=["add", "sub", "mult", "div", "pow"],
)
def test_binary_operator_rendering(render, node, expected):
    assert render(node) == expected


def test_binary_operator_pre_and_post_wrap(render):
    node = AddOp(left=Constant(1), right=Constant(2), pre="(", post=")")
    assert render(node) == "(1+2)"


def test_floor_op_has_no_handler_and_falls_back(render):
    # FloorOp (and ModuloOp) are not registered in BaseRenderer; they hit
    # render_unknown and stringify. Pinning current behavior; if a handler is
    # added, update this test.
    out = render(FloorOp(left=Constant(1), right=Constant(2)))
    assert out.startswith("FloorOp(")


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "node,expected",
    [
        (GtOp(), ">"),
        (GtEOp(), ">="),
        (LtOp(), "<"),
        (LtEOp(), "<="),
        (EqOp(), "=="),
        (NeqOp(), "!="),
    ],
    ids=["gt", "gte", "lt", "lte", "eq", "neq"],
)
def test_comparison_operator_symbols(render, node, expected):
    assert render(node, current_mode="sym") == expected


# ---------------------------------------------------------------------------
# FunctionCall
# ---------------------------------------------------------------------------

def test_function_call_suppresses_main_namespace(render):
    node = FunctionCall(
        namespace=Name("__main__", "__main__"),
        function_name=Name("sin", "sin"),
        args=deque([Constant(2)]),
    )
    assert render(node, current_mode="sym") == " sin(2) "


def test_function_call_with_namespace(render):
    node = FunctionCall(
        namespace=Name("math", "math"),
        function_name=Name("sin", "sin"),
        args=deque([Constant(2)]),
    )
    assert render(node, current_mode="sym") == " math.sin(2) "


# ---------------------------------------------------------------------------
# InlineComment
# ---------------------------------------------------------------------------

def test_inline_comment_rendering(render):
    assert render(InlineComment("a note")) == " (a note)"


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def test_import_plain(render):
    node = Import(names=deque([Name("math", None)]))
    assert render(node) == "[Python import]: import math\n\n"


def test_import_from_module(render):
    node = Import(
        import_from=True,
        import_from_module="math",
        import_from_level=0,
        names=deque([Name("sqrt", None), Name("pi", None)]),
    )
    assert render(node) == "[Python import]: from math import sqrt, pi\n\n"


# ---------------------------------------------------------------------------
# Comment nodes
# ---------------------------------------------------------------------------

def test_comment_line_appends_newline(render):
    assert render(CommentLine(content="a note")) == "a note\n"


def test_inline_command_mutates_line_context_and_renders_empty(renderer, make_context):
    node = InlineCommand(content="hc: precision=3", commands={"precision": 3})
    ctx = make_context()
    assert renderer.render(node, ctx) == ""
    assert ctx.line_context.precision == 3


def test_comment_command_renders_empty(renderer, make_context):
    # The command node itself renders to an empty string (its effect is on the
    # context, verified separately below).
    node = CommentCommand(commands={"decimals": 2})
    assert renderer.render(node, make_context()) == ""


@pytest.mark.xfail(
    strict=True,
    reason="render_comment_command reassigns global_context via "
    "RenderContext.__or__, which jams the merged dict into the `space` "
    "positional instead of setting `decimals`; see the union bug.",
)
def test_comment_command_mutates_global_context(renderer, make_context):
    node = CommentCommand(commands={"decimals": 2})
    ctx = make_context()
    renderer.render(node, ctx)
    assert ctx.global_context.decimals == 2


# ---------------------------------------------------------------------------
# CalcLine
#
# NOTE: CalcLine rendering requires `param_line` to be seeded on the context.
# From a clean/default context the `toggle_param_line` sym-rule raises (see the
# clean-context xfail below); these tests seed it to exercise the render logic.
# ---------------------------------------------------------------------------

def _calc_c_equals_a_plus_2():
    return CalcLine(
        assigns=deque([Name("c", 5)]),
        expression_tree=deque([AddOp(left=Name("a", 3), right=Constant(2))]),
    )


def test_calc_line_full_mode(render):
    assert render(_calc_c_equals_a_plus_2(), param_line=False) == "c = a+2 = 3+2 = 5\n"


def test_calc_line_symbolic_only_mode(render):
    # Current behavior: assigns and result columns are omitted; a leading
    # " = " prefix remains. Pinned as-is.
    assert render(_calc_c_equals_a_plus_2(), param_line=False, mode="sym") == " = a+2\n"


def test_calc_line_numeric_only_mode(render):
    assert render(_calc_c_equals_a_plus_2(), param_line=False, mode="num") == " = 3+2\n"


def test_calc_line_param_line_single_constant(render):
    node = CalcLine(assigns=deque([Name("a", 2)]), expression_tree=deque([Constant(2)]))
    assert render(node, param_line=False) == "a = 2\n"


def test_calc_line_ignore_short_circuits(render):
    assert render(_calc_c_equals_a_plus_2(), param_line=False, ignore=True) == ""


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def test_if_block_renders_header_and_lines(render):
    param = CalcLine(assigns=deque([Name("a", 2)]), expression_tree=deque([Constant(2)]))
    node = IfBlock(
        lines=deque([param]),
        test=Compare(deque([Constant(2), LtEOp, Name("a", 3), LtOp, Constant(5)])),
        is_true=True,
    )
    assert render(node, param_line=False) == "Since (2<=a<5) -> (2<=3<5) is True:\na = 2\n"


def test_elif_block_selects_true_clause(render):
    winner = IfBlock(
        lines=deque([CalcLine(assigns=deque([Name("d", 5)]), expression_tree=deque([Constant(5)]))]),
        test=Compare(deque([Name("a", 3), GtOp, Constant(2)])),
        is_true=True,
    )
    loser = IfBlock(
        lines=deque([CalcLine(assigns=deque([Name("d", 6)]), expression_tree=deque([Constant(6)]))]),
        test=Compare(deque([Name("a", 3), GtOp, Constant(9)])),
        is_true=False,
    )
    node = ElifBlock(lines=deque([loser, winner]))
    out = render(node, param_line=False)
    assert "is True:" in out
    assert "d = 5" in out
    assert "d = 6" not in out


def test_elif_block_no_true_clause_message(render):
    loser = IfBlock(
        lines=deque([CalcLine(assigns=deque([Name("d", 6)]), expression_tree=deque([Constant(6)]))]),
        test=Compare(deque([Name("a", 3), GtOp, Constant(9)])),
        is_true=False,
    )
    node = ElifBlock(lines=deque([loser]))
    assert render(node, param_line=False) == (
        "No conditions were satisfied within the if-elif block"
    )


# ---------------------------------------------------------------------------
# Documented bugs (xfail)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="toggle_param_line reads context.param_line with no default, so a "
    "CalcLine cannot render from a clean context (AttributeError). This also "
    "breaks the real HandCalcs pipeline on a plain calc line.",
)
def test_calc_line_renders_from_clean_context(render):
    assert render(_calc_c_equals_a_plus_2()) == "c = a+2 = 3+2 = 5\n"


@pytest.mark.xfail(
    strict=True,
    reason="render_exprline sets current_mode on the throwaway `.current` "
    "snapshot rather than the line context, so nested Name renders raise "
    "ContextKeyError.",
)
def test_expr_line_rendering(render):
    node = ExprLine(
        expression_tree=deque([
            FunctionCall(
                namespace=Name("__main__", "__main__"),
                function_name=Name("print", "print"),
                args=deque([Name("d", 4)]),
            )
        ])
    )
    render(node, param_line=False)

@pytest.mark.xfail(
    strict=True,
    reason="render_markdown_comment returns node.comment, but MarkdownComment "
    "has attribute `content`, raising AttributeError.",
)
def test_markdown_comment_rendering(render):
    assert render(MarkdownComment(content="A heading")) == "A heading"


@pytest.mark.xfail(
    strict=True,
    reason="render_compare passes the RenderContext (context) rather than the "
    "BaseRenderContext into the recursive render, so downstream handlers fail "
    "on context.current (AttributeError).",
)
def test_compare_rendering(render):
    node = Compare(deque([Name("a", 3), GtOp, Constant(2)]))
    assert render(node, current_mode="sym") == "a>2"
