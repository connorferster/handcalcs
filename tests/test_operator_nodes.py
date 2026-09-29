"""
Layer-1 data-model tests for arithmetic and comparison operator nodes:
default ``symbol``/``pre``/``post`` and the ``type`` discriminant.
"""
import pytest

from handcalcs.parsing.nodes import Constant
from collections import deque

from handcalcs.parsing.operator_nodes import (
    HcBinOp,
    PowOp,
    DivOp,
    FloorOp,
    ModuloOp,
    MultOp,
    AddOp,
    SubOp,
    HcUnaryOp,
    HcCompOp,
    EqOp,
    NeqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    IsOp,
    IsNotOp,
    InOp,
    NotInOp,
    HcBoolOp,
    AndOp,
    OrOp,
)
from handcalcs.parsing.nodes import HcNode


@pytest.mark.parametrize(
    "cls,symbol,type_str",
    [
        (PowOp, "**", "pow_op"),
        (DivOp, "/", "div_op"),
        (FloorOp, "//", "floor_op"),
        (ModuloOp, "%", "modulo_op"),
        (MultOp, "*", "mult_op"),
        (AddOp, "+", "add_op"),
        (SubOp, "-", "sub_op"),
    ],
    ids=["pow", "div", "floor", "modulo", "mult", "add", "sub"],
)
def test_binary_operator_defaults(cls, symbol, type_str):
    node = cls(left=Constant(1), right=Constant(2))
    assert node.left == Constant(1)
    assert node.right == Constant(2)
    assert node.symbol == symbol
    assert node.type == type_str
    assert node.pre == ""
    assert node.post == ""


def test_binary_operator_pre_post_settable():
    node = AddOp(left=Constant(1), right=Constant(2), pre="(", post=")")
    assert (node.pre, node.post) == ("(", ")")


def test_binop_base_is_hcnode_subclass():
    assert issubclass(AddOp, HcBinOp)


def test_unary_operator_defaults():
    node = HcUnaryOp(operand=Constant(10))
    assert node.operand == Constant(10)
    assert node.symbol == "-"
    assert node.type == "unary_op"
    assert node.pre == ""
    assert node.post == ""


def test_unary_operator_symbol_settable():
    node = HcUnaryOp(operand=Constant(10), symbol="~")
    assert node.symbol == "~"


def test_unary_operator_is_hcnode_subclass():
    assert issubclass(HcUnaryOp, HcNode)


@pytest.mark.parametrize(
    "cls,symbol,type_str",
    [
        (EqOp, "==", "eq_op"),
        (NeqOp, "!=", "neq_op"),
        (GtOp, ">", "gt_op"),
        (GtEOp, ">=", "gte_op"),
        (LtOp, "<", "lt_op"),
        (LtEOp, "<=", "lte_op"),
    ],
    ids=["eq", "neq", "gt", "gte", "lt", "lte"],
)
def test_comparison_operator_defaults(cls, symbol, type_str):
    node = cls()
    assert node.symbol == symbol
    assert node.type == type_str


def test_compop_base_is_hcnode_subclass():
    assert issubclass(EqOp, HcCompOp)


def test_comparison_operator_type_readable_on_class():
    # The parser stores bare operator *classes* (not instances) in a Compare
    # deque; the render handlers rely on `type`/`symbol` being class-readable.
    assert GtOp.type == "gt_op"
    assert GtOp.symbol == ">"


@pytest.mark.parametrize(
    "cls,symbol,type_str",
    [
        (IsOp, " is ", "is_op"),
        (IsNotOp, " is not ", "is_not_op"),
        (InOp, " in ", "in_op"),
        (NotInOp, " not in ", "not_in_op"),
    ],
    ids=["is", "is_not", "in", "not_in"],
)
def test_identity_membership_operator_defaults(cls, symbol, type_str):
    # Identity/membership ops live in a Compare deque like the relational ops,
    # but being word operators their symbols carry their own surrounding spaces.
    node = cls()
    assert node.symbol == symbol
    assert node.type == type_str
    assert cls.symbol == symbol
    assert cls.type == type_str


def test_identity_membership_ops_are_compop_subclasses():
    for cls in (IsOp, IsNotOp, InOp, NotInOp):
        assert issubclass(cls, HcCompOp)


@pytest.mark.parametrize(
    "cls,symbol,type_str",
    [
        (AndOp, "and", "and_op"),
        (OrOp, "or", "or_op"),
    ],
    ids=["and", "or"],
)
def test_boolean_operator_defaults(cls, symbol, type_str):
    node = cls(values=deque([Constant(1), Constant(2)]))
    assert node.values == deque([Constant(1), Constant(2)])
    assert node.symbol == symbol
    assert node.type == type_str
    assert node.pre == ""
    assert node.post == ""


def test_boolean_operator_is_hcboolop_subclass():
    assert issubclass(AndOp, HcBoolOp)
    assert issubclass(OrOp, HcBoolOp)
    assert issubclass(HcBoolOp, HcNode)


def test_boolean_operator_is_n_ary():
    # A BoolOp holds an arbitrary number of operands (a and b and c).
    node = AndOp(values=deque([Constant(1), Constant(2), Constant(3)]))
    assert len(node.values) == 3
