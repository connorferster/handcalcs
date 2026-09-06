"""
Test suite for handcalcs.renderers.base.infix_binop.

`infix_binop` renders a BinOp tree back into an infix string, inserting
parentheses only where they are required to preserve the tree's meaning.
The rules it must honour:

* Precedence: a lower-precedence operand of a higher-precedence operator is
  parenthesised (e.g. ``(a + b) * c``); the reverse is not (``a + b * c``).
* Associativity: an operand on the "wrong" side of a left/right-associative
  operator that would otherwise re-associate is parenthesised
  (``a - (b - c)``, ``a ** (b ** c)`` stays but ``2 ** 3 ** 4`` needs none).
* Commutativity: for equal-precedence, non-commutative operators
  (``-``, ``/``, ``//``, ``%``), the right operand is parenthesised so the
  operation is not silently re-associated.

Run with:
    uv run pytest tests/test_infix.py
"""

import pytest

from handcalcs.renderers.base import BaseRenderer, infix_binop
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.operator_nodes import (
    AddOp,
    SubOp,
    MultOp,
    DivOp,
    FloorOp,
    ModuloOp,
    PowOp,
)


@pytest.fixture
def render():
    """Return a helper that renders a BinOp tree to its infix string."""
    renderer = BaseRenderer()
    # lpar/rpar are consumed by infix_binop but are not standard
    # RenderContext attributes, so they are injected as extra context kwargs.
    base_context = renderer.create_context(
        lpar="(", rpar=")", current_mode="sym"
    )

    def _render(node):
        return infix_binop(node, renderer, allow_spaces=True, base_context=base_context)

    return _render


def c(value):
    """Shorthand for a Constant operand."""
    return Constant(value)


# --- Precedence -------------------------------------------------------------

def test_simple_add(render):
    # a + b -> no parentheses needed
    assert render(AddOp(c(1), c(2))) == "1 + 2"


def test_precedence_add_then_mult(render):
    # a + b * c -> b * c binds tighter, so it is NOT parenthesised
    assert render(AddOp(c(1), MultOp(c(2), c(3)))) == "1 + 2 * 3"


def test_precedence_mult_of_add(render):
    # (a + b) * c -> the lower-precedence a + b SHOULD be parenthesised
    assert render(MultOp(AddOp(c(1), c(2)), c(3))) == "(1 + 2) * 3"


# --- Associativity ----------------------------------------------------------

def test_left_assoc_subtraction(render):
    # (a - b) - c -> left-associative, so no extra parentheses
    assert render(SubOp(SubOp(c(1), c(2)), c(3))) == "1 - 2 - 3"


def test_right_assoc_pow(render):
    # a ** (b ** c): ** is right-associative, so the parentheses here are
    # redundant (2 ** 3 ** 4 already means 2 ** (3 ** 4)). infix_binop treats
    # ** as non-commutative and parenthesises the equal-precedence right
    # operand regardless of associativity, so the parentheses are emitted.
    # This documents the current behaviour rather than the minimal form.
    assert render(PowOp(c(2), PowOp(c(3), c(4)))) == "2 ** (3 ** 4)"


# --- Commutativity (non-commutative right operand) --------------------------

def test_non_commutative_sub_on_right(render):
    # a - (b - c) -> right operand SHOULD be parenthesised (- not commutative)
    assert render(SubOp(c(1), SubOp(c(2), c(3)))) == "1 - (2 - 3)"


def test_non_commutative_div_on_right(render):
    # a / (b / c) -> right operand SHOULD be parenthesised (/ not commutative)
    assert render(DivOp(c(1), DivOp(c(2), c(3)))) == "1 / (2 / 3)"


def test_non_commutative_floor_on_right(render):
    # a // (b // c) -> right operand SHOULD be parenthesised (// not commutative)
    assert render(FloorOp(c(1), FloorOp(c(2), c(3)))) == "1 // (2 // 3)"


def test_non_commutative_modulo_on_right(render):
    # a % (b % c) -> right operand SHOULD be parenthesised (% not commutative)
    assert render(ModuloOp(c(1), ModuloOp(c(2), c(3)))) == "1 % (2 % 3)"


# --- Full BEDMAS: every Python arithmetic operator in one nested tree -------

def test_full_bedmas_nesting(render):
    # Tree exercising all seven arithmetic operators (+ - * / // % **) across
    # multiple precedence levels:
    #
    #     (1 + 2) * 3 ** 4 - 5 / 6 // 7 % 8
    #
    #   - top:   SubOp
    #   - left:  MultOp( AddOp(1, 2), PowOp(3, 4) )
    #              -> AddOp parenthesised (lower precedence under *),
    #                 PowOp left as-is (higher precedence, binds tighter)
    #   - right: ModuloOp( FloorOp( DivOp(5, 6), 7 ), 8 )
    #              -> all equal precedence, left-associative on the left
    #                 branch, so no parentheses are required
    node = SubOp(
        MultOp(AddOp(c(1), c(2)), PowOp(c(3), c(4))),
        ModuloOp(FloorOp(DivOp(c(5), c(6)), c(7)), c(8)),
    )
    assert render(node) == "(1 + 2) * 3 ** 4 - 5 / 6 // 7 % 8"
