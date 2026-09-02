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
from decimal import Decimal

import pytest

from handcalcs.renderers.base import ContextKeyError, ContextValueError
from handcalcs.parsing.nodes import Name, Constant, List, Tuple, Set, Dictionary, Attribute
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
    Heading,
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
# Attribute (no handler registered)
# ---------------------------------------------------------------------------

def test_attribute_has_no_handler_raises(render):
    # Attribute is defined in nodes.py but no BaseRenderer handler is registered
    # for it yet, so render_node raises NotImplementedError. Pinning current
    # behavior; add/adjust when an 'attribute' handler is implemented.
    with pytest.raises(NotImplementedError):
        render(Attribute("math", "pi", 3.14159), current_mode="num")


# ---------------------------------------------------------------------------
# Name value renderability (numeric mode)
#
# In numeric mode, render_name renders ``node.value`` via ``render_node`` when
# the value is itself an HcNode (e.g. a collection literal), and otherwise
# formats/stringifies the raw Python value. These tests exercise both paths for
# the basic collection nodes, plain int/float, float-like objects (complex,
# Decimal, forallpeople Physical), and an arbitrary custom object.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        (List(deque([Constant(1), Constant(2), Constant(3)])), "[1, 2, 3]"),
        (List(deque([])), "[]"),
        (Set(deque([Constant(1)])), "{1}"),
        (Tuple(deque([Constant(1), Constant(2)])), "(1, 2)"),
        (Dictionary(deque([Constant(1)]), deque([Constant(2)])), "{1: 2}"),
    ],
    ids=["list", "empty-list", "set", "tuple", "dict"],
)
def test_name_value_renders_collection_node(render, value, expected):
    # A Name bound to a collection literal renders the collection in numeric
    # mode (render_name delegates to render_node for HcNode values).
    assert render(Name("x", value), current_mode="num") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (4, "4"),
        (-7, "-7"),
        (0, "0"),
        (3.14159, "3.1416"),
        (2.0, "2"),
    ],
    ids=["int", "neg-int", "zero", "float", "float-whole"],
)
def test_name_value_renders_int_and_float(render, value, expected):
    # Plain ints/floats are not HcNodes, so render_name falls back to formatting
    # the raw value with the context format code (default ".5g").
    assert render(Name("n", value), current_mode="num") == expected


def test_name_value_complex_renders(render):
    # complex is not a node; the ".5g" format code applies to it.
    assert render(Name("z", complex(1, 2)), current_mode="num") == "1+2j"


def test_name_value_decimal_renders(render):
    # Decimal supports the ".5g" format code like a float.
    assert render(Name("d", Decimal("3.14159")), current_mode="num") == "3.1416"


def test_name_value_physical_renders(render):
    # A forallpeople Physical is float-like: it honours the ".5g" format code
    # and renders with its unit.
    si = pytest.importorskip("forallpeople")
    si.environment("default")
    assert render(Name("F", 5000 * si.N), current_mode="num") == "5 kN"


def test_name_value_custom_object_falls_back_to_str(render):
    # An arbitrary object rejects the format code (TypeError) and has no node
    # handler, so render_name falls back to its string representation.
    class Widget:
        def __repr__(self):
            return "Widget(repr)"

        def __str__(self):
            return "a widget"

    assert render(Name("w", Widget()), current_mode="num") == "a widget"


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


def test_floor_op_has_no_handler_raises(render):
    # FloorOp (and ModuloOp) are not registered in BaseRenderer. An unregistered
    # node type is a programming error rather than something to stringify, so
    # render_node raises NotImplementedError. If a handler is added, update this.
    with pytest.raises(NotImplementedError):
        render(FloorOp(left=Constant(1), right=Constant(2)))


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
    # A comment is a component atom; the separating space is supplied by the
    # join step, not embedded in the atom.
    assert render(InlineComment("a note")) == "(a note)"


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def test_import_plain(render):
    node = Import(names=deque([Name("math", None)]))
    assert render(node) == ["[Python import]:", "import", "math"]


def test_import_from_module(render):
    node = Import(
        import_from=True,
        import_from_module="math",
        import_from_level=0,
        names=deque([Name("sqrt", None), Name("pi", None)]),
    )
    assert render(node) == ["[Python import]:", "from", "math", "import", "sqrt, pi"]


# ---------------------------------------------------------------------------
# Comment nodes
# ---------------------------------------------------------------------------

def test_comment_line_renders_as_bare_string(render):
    # A comment line is a single string in the master list; the trailing newline
    # is added by the join step, not the handler.
    assert render(CommentLine(content="a note")) == "a note"


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


def test_comment_command_mutates_global_context(renderer, make_context):
    node = CommentCommand(commands={"decimals": 2})
    ctx = make_context()
    renderer.render(node, ctx)
    assert ctx.global_context.decimals == 2


# ---------------------------------------------------------------------------
# CalcLine
#
# A CalcLine renders as a list of string components (columns interleaved with
# the equality symbol); spaces/indent/newline are inserted by the join step.
# ---------------------------------------------------------------------------

def _calc_c_equals_a_plus_2():
    return CalcLine(
        assigns=deque([Name("c", 5)]),
        expression_tree=deque([AddOp(left=Name("a", 3), right=Constant(2))]),
    )


def test_calc_line_full_mode(render):
    assert render(_calc_c_equals_a_plus_2(), param_line=False) == [
        "c", "=", "a+2", "=", "3+2", "=", "5",
    ]


def test_calc_line_symbolic_only_mode(render):
    # Symbolic-only mode: just the symbolic column, no assign/num/result.
    assert render(_calc_c_equals_a_plus_2(), param_line=False, mode="sym") == ["a+2"]


def test_calc_line_numeric_only_mode(render):
    # Numeric-only mode: just the numeric-substitution column.
    assert render(_calc_c_equals_a_plus_2(), param_line=False, mode="num") == ["3+2"]


def test_calc_line_param_line_single_constant(render):
    node = CalcLine(assigns=deque([Name("a", 2)]), expression_tree=deque([Constant(2)]))
    assert render(node, param_line=False) == ["a", "=", "2"]


def test_calc_line_ignore_short_circuits(render):
    assert render(_calc_c_equals_a_plus_2(), param_line=False, ignore=True) == ""


# ---------------------------------------------------------------------------
# ExprLine (bare expression statements: no assignment, so no result column)
# ---------------------------------------------------------------------------

def test_expr_line_statement_call_shows_symbolic_and_numeric(render):
    # A statement call renders `sym = num` (substitution view), with no
    # trailing equals and no fabricated result.
    node = ExprLine(
        expression_tree=deque([
            FunctionCall(
                namespace=Name("__main__", "__main__"),
                function_name=Name("print", "print"),
                args=deque([Name("d", 4)]),
            )
        ])
    )
    assert render(node) == [" print(d) ", "=", " print(4) "]


def test_expr_line_value_bearing_expression(render):
    node = ExprLine(expression_tree=deque([AddOp(left=Name("x", 10), right=Name("y", 20))]))
    assert render(node) == ["x+y", "=", "10+20"]


def test_expr_line_return_is_symbolic_only(render):
    # A return statement lives in a symbolic function definition: symbolic form
    # only, no numeric substitution (its names have no runtime value).
    node = ExprLine(
        expression_tree=deque([AddOp(left=Name("pi"), right=Constant(1))]),
        return_expr=True,
    )
    assert render(node) == ["pi+1"]


def test_expr_line_docstring_renders_as_plain_line(render):
    # A bare string statement parses to a single Constant holding the string.
    node = ExprLine(expression_tree=deque([Constant("Module note.")]))
    assert render(node) == ["Module note."]


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def test_if_block_renders_header_and_lines(render):
    # A block renders as ``[header_string, body_list]`` -- the body lines in
    # their own nested sublist. Indent/newlines are applied later, by join.
    param = CalcLine(assigns=deque([Name("a", 2)]), expression_tree=deque([Constant(2)]))
    node = IfBlock(
        lines=deque([param]),
        test=Compare(deque([Constant(2), LtEOp, Name("a", 3), LtOp, Constant(5)])),
        is_true=True,
    )
    assert render(node, param_line=False) == [
        "Since (2<=a<5) -> (2<=3<5) is True:",
        [["a", "=", "2"]],
    ]


def test_if_block_multiple_lines(render):
    node = IfBlock(
        lines=deque([
            CalcLine(assigns=deque([Name("a", 2)]), expression_tree=deque([Constant(2)])),
            CalcLine(assigns=deque([Name("b", 3)]), expression_tree=deque([Constant(3)])),
        ]),
        test=Compare(deque([Name("a", 3), GtOp, Constant(2)])),
        is_true=True,
    )
    assert render(node, param_line=False) == [
        "Since (a>2) -> (3>2) is True:",
        [["a", "=", "2"], ["b", "=", "3"]],
    ]


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
    # The elif block renders only the selected (true) clause's [header, body].
    assert render(node, param_line=False) == [
        "Since (a>2) -> (3>2) is True:",
        [["d", "=", "5"]],
    ]


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
# Previously-buggy paths, now fixed
# ---------------------------------------------------------------------------

def test_calc_line_renders_from_clean_context(render):
    # A CalcLine as the very first rendered node (no param_line seeded) must
    # render rather than raise; the calc_line:pre rule defaults param_line.
    assert render(_calc_c_equals_a_plus_2()) == ["c", "=", "a+2", "=", "3+2", "=", "5"]


def test_heading_rendering(render):
    # A heading renders as a single markdown string, its level reproduced from
    # the node's heading_level.
    assert render(Heading(content="A heading", heading_level=2)) == "## A heading"


def test_compare_rendering(render):
    node = Compare(deque([Name("a", 3), GtOp, Constant(2)]))
    assert render(node, current_mode="sym") == "a>2"
