"""
Layer-1 data-model tests for arithmetic and comparison operator nodes:
default ``symbol``/``pre``/``post`` and the ``type`` discriminant.
"""
import pytest

from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.operator_nodes import (
    HcBinOp,
    PowOp,
    DivOp,
    FloorOp,
    ModuloOp,
    MultOp,
    AddOp,
    SubOp,
    HcCompOp,
    EqOp,
    NeqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
)


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
