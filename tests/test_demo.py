"""
End-to-end regression tests for HandCalcs.demo().

demo() renders a fixed source string through the current renderer; it doubles as
a showcase and a guardrail. These tests pin the five inconsistencies the demo
surfaced (unary operators, line-break comments, heading levels, param-line
collapse for collections, and float formatting inside collections) so they don't
regress.
"""
import pytest

from handcalcs import HandCalcs, PlainTextRenderer


@pytest.fixture(scope="module")
def demo_tree():
    # demo() returns the rendered tree (a nested list of components), not joined
    # text, so a caller can post-process it before joining.
    return HandCalcs(PlainTextRenderer()).demo()


@pytest.fixture(scope="module")
def demo_output():
    # The joined-text form of the demo tree, used for the substring assertions
    # below.
    hc = HandCalcs(PlainTextRenderer())
    return hc.renderer.join(hc.demo())


def test_demo_returns_render_tree(demo_tree):
    # demo() returns the rendered tree (a list), which the caller joins.
    assert isinstance(demo_tree, list) and demo_tree


def test_demo_renders_without_error(demo_output):
    assert isinstance(demo_output, str) and demo_output


# --- #1 Unary operators -----------------------------------------------------

def test_demo_unary_no_notimplemented_leak(demo_output):
    # A dropped unary operand used to leave empty columns like "b =  =  =".
    assert "=  =  =" not in demo_output
    assert "not_implemented" not in demo_output
    assert "NoValue" not in demo_output


def test_demo_unary_renders_negation(demo_output):
    # -b appears symbolically, and its numeric substitution reads -(-10.423),
    # never the ambiguous --10.423.
    assert "(-b +" in demo_output
    assert "--10.423" not in demo_output
    assert "(-(-10.423) +" in demo_output


# --- #2 Line-break comments -------------------------------------------------

def test_demo_line_break_is_single_blank_line(demo_output):
    # A `# hc: -b` directive inserts exactly one blank line, never a double.
    assert "\n\n\n" not in demo_output


# --- #3 Heading levels ------------------------------------------------------

def test_demo_heading_levels_exclude_comment_marker(demo_output):
    # The top heading is level 1 (`# `), the section headings level 2 (`## `);
    # the comment-marker '#' is no longer counted into the level.
    assert "# HandCalcs v2.0 Demo\n" in demo_output
    assert "## The quadratic formula\n" in demo_output
    assert "### The quadratic formula\n" not in demo_output


# --- #4 Collection assignments collapse to a param line ---------------------

@pytest.mark.parametrize(
    "line",
    [
        "x_values = [1, 2, 3, 4, 5]\n",
        "a_dictionary = {cat: 1, hat: 2, bat: 3.1416}\n",
        "a_tuple = (string, 1, 42, 3+4j)\n",
    ],
    ids=["list", "dict", "tuple"],
)
def test_demo_literal_collections_are_param_lines(demo_output, line):
    # No symbolic/numeric substitution columns: the literal collection appears
    # exactly once (single column), so the doubled form must be absent.
    assert line in demo_output
    doubled = line.rstrip("\n")
    assert f"{doubled} = {doubled}" not in demo_output


# --- #5 Float formatting inside collections ---------------------------------

def test_demo_collection_floats_are_formatted(demo_output):
    # The accumulated list must be formatted element-wise (default .5g), not a
    # full-precision Python repr.
    assert "11.31" in demo_output
    assert "11.309932474020215" not in demo_output
    # The scalar result on the same page must also be formatted.
    assert "78.69006752597979" not in demo_output
