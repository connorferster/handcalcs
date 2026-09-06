"""
Exploratory tests for handcalcs.renderers.base.infix_binop.

These are debug-harness tests: each one builds a BinOp tree, calls
infix_binop, prints the produced string, then `assert False` so that
pytest surfaces the captured stdout in the failure report.

Run with:
    uv run pytest tests/infix.py

NOTE: as of writing, `infix_binop` does not import cleanly (several
syntax errors in base.py around lines 640-705) and, once those are
fixed, has runtime bugs (undefined `render_node`, `ModOp`, missing
`context.lpar/rpar`, etc.). Until the import succeeds, pytest will
report a collection error rather than the prints below.
"""

from handcalcs.renderers.base import BaseRenderer, infix_binop
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.operator_nodes import (
    AddOp,
    SubOp,
    MultOp,
    DivOp,
    PowOp,
)


def make_context():
    """A BaseRenderContext whose `.current` carries lpar/rpar/space/format."""
    renderer = BaseRenderer()
    # lpar/rpar are consumed by infix_binop but are not standard RenderContext
    # attributes, so inject them as extra context kwargs.
    base_context = renderer.create_context(lpar="(", rpar=")", current_mode="sym")
    return renderer, base_context


def c(value):
    """Shorthand for a Constant operand."""
    return Constant(value)


def show(label, node):
    renderer, base_context = make_context()
    result = infix_binop(node, renderer, allow_spaces=True,      base_context=base_context)
    print(f"\n[{label}] -> {result!r}")
    assert False, f"{label}: {result!r}"


def test_simple_add():
    # a + b
    show("simple_add", AddOp(left=c(1), right=c(2)))


def test_precedence_add_then_mult():
    # a + b * c  -> the b*c should NOT be parenthesised
    node = AddOp(left=c(1), right=MultOp(left=c(2), right=c(3)))
    show("add_then_mult", node)


def test_precedence_mult_of_add():
    # (a + b) * c  -> the a+b SHOULD be parenthesised
    node = MultOp(left=AddOp(left=c(1), right=c(2)), right=c(3))
    show("mult_of_add", node)


def test_left_assoc_subtraction():
    # a - b - c  -> parsed left-assoc: (a - b) - c ; no extra parens expected
    node = SubOp(left=SubOp(left=c(1), right=c(2)), right=c(3))
    show("left_assoc_sub", node)


def test_non_commutative_sub_on_right():
    # a - (b - c)  -> right operand SHOULD be parenthesised (sub not commutative)
    node = SubOp(left=c(1), right=SubOp(left=c(2), right=c(3)))
    show("non_commutative_sub_right", node)


def test_non_commutative_div_on_right():
    # a / (b / c)  -> right operand SHOULD be parenthesised (div not commutative)
    node = DivOp(left=c(1), right=DivOp(left=c(2), right=c(3)))
    show("non_commutative_div_right", node)


def test_right_assoc_pow():
    # a ** b ** c  -> parsed right-assoc: a ** (b ** c) ; no extra parens expected
    node = PowOp(left=c(2), right=PowOp(left=c(3), right=c(4)))
    show("right_assoc_pow", node)
