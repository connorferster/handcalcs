"""
End-to-end tests for ASCIIRenderer-specific rendering: symbol swaps (superscript
powers and division, which the base renderer leaves as ``**``/``/``), underlined
headings and calc lines aligned on their first ``=``.
"""
import pytest

from handcalcs import HandCalcs, ASCIIRenderer, get_renderer


@pytest.fixture
def render_plain():
    def _render(source):
        # Return the last rendered (non-empty) line for a small snippet.
        out = HandCalcs(ASCIIRenderer())(source)
        return out.splitlines()[-1]

    return _render


@pytest.mark.parametrize(
    "source,expected",
    [
        ("a=2\nb=3\ny = b**2\n", "y = b² = 3² = 9"),
        ("a=2\nb=3\ny = (a + b)**2\n", "y = (a + b)² = (2 + 3)² = 25"),
        ("b=3\nw = 2 * b**3\n", "w = 2 * b³ = 2 * 3³ = 54"),
    ],
    ids=["simple", "parenthesized-base", "nested"],
)
def test_superscript_power_has_no_stray_spaces(render_plain, source, expected):
    # A constant exponent becomes a superscript attached to the base (no "b  ²").
    assert render_plain(source) == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("a=8\nz = a / 4\n", "z = a / 4 = 8 / 4 = 2"),
        ("z = 4 / 2\n", "z = 4 / 2 = 2"),
        ("a=8\nb=3\nc=2\nz = a / (b + c)\n", "z = a / (b + c) = 8 / (3 + 2) = 1.6"),
    ],
    ids=["constant-denominator", "both-constant", "parenthesized-denominator"],
)
def test_division_keeps_slash(render_plain, source, expected):
    # Division always renders with its '/' symbol, even with constant operands.
    assert render_plain(source) == expected


def test_params_block_with_comments_aligns_columns():
    # ``# hc: -h`` keeps comments; ids right-align and ``=`` lines up per column,
    # with one space before a comment and a wider gap between cells.
    src = "# hc: -h\nx = 3 # one\nlonger = 4000\nz = 5 # last\nw = 6\nqq = 77 # c\nr = 1\n"
    out = HandCalcs(ASCIIRenderer())(src).splitlines()
    assert out == [
        "x = 3 (one)    longer = 4000        z = 5 (last)",
        "w = 6              qq = 77   (c)    r = 1",
    ]


def render_ascii(source, renderer=None):
    return HandCalcs(renderer or ASCIIRenderer())(source)


def test_registered_as_ascii():
    assert get_renderer("ascii") is ASCIIRenderer


def test_heading_levels_are_underlined():
    # `##` is level 1 (over- and underlined), `###` level 2, `####` level 3 and
    # deeper levels share the last rule. Each heading is set off by blank lines,
    # except at the very top.
    out = render_ascii(
        "## Beam\n### Loads\na = 1\n#### Dead\nb = 2\n##### Note\n###### Deeper\n"
    )
    assert out == (
        "====\nBeam\n====\n\n"
        "Loads\n=====\n\n"
        "a = 1\n\n"
        "Dead\n----\n\n"
        "b = 2\n\n"
        "Note\n~~~~\n\n"
        "Deeper\n~~~~~~\n\n"
    )


def test_heading_rules_can_be_restyled():
    class Stars(ASCIIRenderer):
        HEADING_RULES = {1: ("*", False)}

    assert render_ascii("### Loads\na = 1\n", Stars()) == "Loads\n*****\n\na = 1\n"


def test_line_break_before_heading_adds_no_extra_blank_line():
    out = render_ascii("a = 1\n# hc: -b\n## Next\nb = 2\n")
    assert out == "a = 1\n\n====\nNext\n====\n\nb = 2\n"


def test_calc_lines_align_on_first_equals():
    out = render_ascii("a = 2\nlong_name = 3 * a\nc = long_name + a  # note\n")
    assert out.splitlines() == [
        "        a = 2",
        "long_name = 3 * a = 3 * 2 = 6",
        "        c = long_name + a = 6 + 2 = 8 (note)",
    ]


def test_alignment_restarts_after_each_heading():
    out = render_ascii("long_name = 1\n### Next\nb = 2\ncc = 3\n")
    assert out.splitlines() == [
        "long_name = 1",
        "",
        "Next",
        "====",
        "",
        " b = 2",
        "cc = 3",
    ]


def test_comment_lines_are_not_padded_and_do_not_break_alignment():
    out = render_ascii("a = 1\n# Some words\nlonger = 2\n")
    assert out.splitlines() == ["     a = 1", "Some words", "longer = 2"]


def test_long_calc_and_params_grid_shift_to_the_common_column():
    out = render_ascii(
        "x = 1; y = 2\nwidth = 4\nd = width * x + y  # hc: -m\n"
    )
    assert out.splitlines() == [
        "    x = 1    y = 2",
        "width = 4",
        "    d = width * x + y",
        "      = 4 * 1 + 2",
        "      = 6",
    ]


def test_conditional_body_aligns_as_its_own_scope():
    # The body of a block is aligned (and indented) on its own; a long calc
    # inside it indents every row.
    out = render_ascii(
        "a = 2\nlonger = 3\nif a > 1:\n    q = a * longer  # hc: -m\n    rr = 1\n"
    )
    assert out.splitlines() == [
        "     a = 2",
        "longer = 3",
        "Since (a>1) -> (2>1) is True:",
        "     q = a * longer",
        "       = 2 * 3",
        "       = 6",
        "    rr = 1",
    ]
