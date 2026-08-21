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
    MarkdownComment,
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


# --- MarkdownComment.from_raw_comment -----------------------------------

def test_markdown_comment_single_hash():
    assert MarkdownComment.from_raw_comment("# Title").content == "Title"


def test_markdown_comment_double_hash_keeps_inner_hash():
    # Regex `^#[ ]*(.+)` consumes only the first '#'; a heading written with
    # '##' therefore keeps the second '#' in its content.
    assert MarkdownComment.from_raw_comment("## A heading").content == "# A heading"


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
