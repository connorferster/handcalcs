"""
Layer-1 data-model tests for line nodes, including the ``from_raw_comment``
constructors on the comment line types.
"""
from collections import deque

import pytest

from handcalcs.parsing.nodes import Name, Constant
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    CommentLine,
    Heading,
    CommentCommand,
    Import,
)
from handcalcs.parsing.inline_nodes import InlineComment


def test_calc_line_defaults():
    cl = CalcLine(assigns=deque([Name("a")]), expression_tree=deque([Constant(1)]))
    assert cl.level == 0
    assert cl.comment is None
    assert cl.pars_nesting is False
    assert cl.type == "calc_line"


def test_calc_line_with_comment():
    cl = CalcLine(
        assigns=deque([Name("a")]),
        expression_tree=deque([Constant(1)]),
        comment=InlineComment("note"),
    )
    assert cl.comment == InlineComment("note")


def test_expr_line_defaults():
    el = ExprLine(expression_tree=deque([Constant(1)]))
    assert el.return_expr is False
    assert el.pars_nesting is False
    assert el.type == "expr_line"


# --- CommentLine.from_raw_comment ---------------------------------------

def test_comment_line_strips_leading_hash_and_space():
    assert CommentLine.from_raw_comment("# a plain note").content == "a plain note"


def test_comment_line_strips_all_leading_hashes():
    # lstrip("# ") removes any run of '#' and ' ' characters.
    assert CommentLine.from_raw_comment("## heading").content == "heading"


# --- Heading.from_raw_comment -------------------------------------------

def test_heading_single_hash():
    heading = Heading.from_raw_comment("# Title")
    assert heading.content == "Title"
    assert heading.heading_level == 1


def test_heading_double_hash_sets_level_and_strips_hashes():
    # The number of leading '#' is the markdown heading level; all '#'s are
    # stripped from the content.
    heading = Heading.from_raw_comment("## A heading")
    assert heading.content == "A heading"
    assert heading.heading_level == 2


# --- CommentCommand.from_raw_comment: kwarg vs flag ---------------------

def test_comment_command_kwarg_style():
    cc = CommentCommand.from_raw_comment("# hc: decimals=2")
    assert cc.commands == {"decimals": 2}
    assert cc.type == "comment_command"


def test_comment_command_flag_style():
    cc = CommentCommand.from_raw_comment("# hc: -f 2g")
    assert cc.commands["format"] == "2g"
    assert cc.commands["multiline"] is False


# --- Import --------------------------------------------------------------

def test_import_defaults():
    imp = Import(names=deque([Name("math", None)]))
    assert imp.import_from is False
    assert imp.import_from_module is None
    assert imp.type == "import"


def test_import_from_fields():
    imp = Import(
        import_from=True,
        import_from_module="math",
        import_from_level=0,
        names=deque([Name("sqrt", None)]),
    )
    assert imp.import_from is True
    assert imp.import_from_module == "math"
    assert imp.import_from_level == 0
