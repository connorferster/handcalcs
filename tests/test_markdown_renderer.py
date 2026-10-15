"""
Tests for the MarkdownRenderer, run through the full HandCalcs pipeline
(source -> parser -> HcSequence -> MarkdownRenderer -> complete()).

- Golden tests: the rendered demo is compared, section by section, against
  ``tests/golden/markdown_demo.md``. After an intended change to the output,
  regenerate it with ``HANDCALCS_UPDATE_GOLDEN=1 uv run pytest tests/test_markdown_renderer.py``
  and review the diff.
- Structural tests pin the Jupyter-specific format (see markdown_renderer_plan.md):
  one-line ``$$`` groups, ``>`` blockquotes for nested blocks, ``&nbsp;`` spacers.
- Focused tests pin the escaping of prose and of text inside math.
- A KaTeX test typesets every math fragment of the demo and of a stress source
  (skipped unless HANDCALCS_KATEX_JS points at a katex.min.js and mini-racer is
  installed; see scripts/markdown_demo_check.py).
"""
import importlib.util
import os
import pathlib
import re

import pytest
from markdown_it import MarkdownIt

from handcalcs import HandCalcs
from handcalcs.renderers.markdown import MarkdownRenderer, markdown_prose, math_prose, math_text

GOLDEN = pathlib.Path(__file__).parent / "golden" / "markdown_demo.md"
UPDATE_GOLDEN = os.environ.get("HANDCALCS_UPDATE_GOLDEN") == "1"


def render(source: str) -> str:
    return HandCalcs(renderer=MarkdownRenderer())(source)


def rows(source: str) -> list[str]:
    """The rows of every ``$$`` math group in the output."""
    found = []
    for group in re.findall(r"\$\$\\begin\{aligned\} (.*?) \\end\{aligned\}\$\$", render(source)):
        found.extend(group.split(" \\\\ "))
    return found


def sections(text: str) -> dict[str, str]:
    """Split a rendered demo into its preamble and ``##`` sections."""
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    named = {}
    for part in parts:
        heading = re.match(r"## (.*)", part)
        named[heading.group(1) if heading else "preamble"] = part
    return named


def paragraph_depths(markdown: str) -> list[tuple[int, str]]:
    """``(blockquote depth, content)`` for every paragraph, as parsed by markdown-it."""
    depth, found = 0, []
    for token in MarkdownIt().parse(markdown):
        if token.type == "blockquote_open":
            depth += 1
        elif token.type == "blockquote_close":
            depth -= 1
        elif token.type == "inline":
            found.append((depth, token.content))
    return found


@pytest.fixture(scope="module")
def demo_output() -> str:
    output = HandCalcs(renderer=MarkdownRenderer()).demo()
    if UPDATE_GOLDEN:
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(output)
    return output


# --- Golden demo --------------------------------------------------------------

GOLDEN_SECTIONS = sections(GOLDEN.read_text()) if GOLDEN.exists() else {}


def test_demo_has_same_sections_as_golden(demo_output):
    if UPDATE_GOLDEN:
        pytest.skip("golden file regenerated")
    assert list(sections(demo_output)) == list(GOLDEN_SECTIONS)


@pytest.mark.parametrize("section", list(GOLDEN_SECTIONS))
def test_demo_section_matches_golden(demo_output, section):
    if UPDATE_GOLDEN:
        pytest.skip("golden file regenerated")
    assert sections(demo_output).get(section) == GOLDEN_SECTIONS[section]


@pytest.mark.parametrize("leak", [
    "\\medskip", "\\noindent", "\\begin{list}", "\\end{list}", "\\section",
    "\\displaystyle", "\\begin{aligned}[t]", "<br>", "\\textasciicircum",
    "\\textbackslash", "\\arcsinh", "``",
])
def test_demo_has_no_latex_text_mode_leaks(demo_output, leak):
    assert leak not in demo_output


def test_demo_math_groups_are_one_line(demo_output):
    for line in demo_output.splitlines():
        if "$$" in line:
            assert line.lstrip("> ").startswith("$$\\begin{aligned} "), line
            assert line.endswith(" \\end{aligned}$$") and line.count("$$") == 2, line


def test_demo_texttt_only_inside_math(demo_output):
    outside_math = re.sub(r"\$\$.*?\$\$|\$.*?\$", "", demo_output)
    assert "\\texttt" not in outside_math


@pytest.mark.parametrize("start, depth", [
    ("\\mathrm{class}_{\\mathrm{section}} &= 3", 2),
    ("\\mathrm{value}_{\\mathrm{computed}} &=", 2),
    ("\\mathrm{acc} &=", 0),
    ("\\mathrm{section}_{\\mathrm{check}} &= 1", 1),
    ("a_{\\mathrm{dictionary}} &=", 0),
])
def test_demo_nesting(demo_output, start, depth):
    found = [
        found_depth for found_depth, content in paragraph_depths(demo_output)
        if content.startswith(f"$$\\begin{{aligned}} {start}")
    ]
    assert found == [depth]


def load_check_script():
    path = pathlib.Path(__file__).parents[1] / "scripts" / "markdown_demo_check.py"
    spec = importlib.util.spec_from_file_location("markdown_demo_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KATEX_STRESS = """\
import math
x = 2.5
a = math.floor(x) + math.ceil(x) # floor & ceil, 50%
b = 7 % 3 # {braces} $dollar$ back\\slash mm^4 a_b #hash ~tilde <tag>
c = x < 3 and x > 1 or not x <= 2
d = math.asinh(x) + math.acosh(x) + math.atanh(0.5)
s = {1, 2}
z = 3 + 4j
w = math.inf
t = 'a_b "q" 50%'
if x < 3:
    if x > 1:
        y = 1 # `code` here
    e = 2
"""


def katex_ready() -> bool:
    return bool(os.environ.get("HANDCALCS_KATEX_JS")) and (
        importlib.util.find_spec("py_mini_racer") is not None
    )


@pytest.mark.skipif(not katex_ready(), reason="HANDCALCS_KATEX_JS or mini-racer not available")
@pytest.mark.parametrize("which", ["demo", "stress"])
def test_math_typesets_with_katex(demo_output, which):
    check = load_check_script()
    markdown = demo_output if which == "demo" else render(KATEX_STRESS)
    assert check.math_fragments(markdown)
    assert check.katex_errors(markdown) == []


# --- Output structure ---------------------------------------------------------

def test_calcs_block_is_one_line_math_group():
    assert render("a = 1\nb = 2\n") == "$$\\begin{aligned} a &= 1 \\\\ b &= 2 \\end{aligned}$$\n"


def test_all_ignored_calcs_block_emits_no_group():
    assert render("acc = [] # hc: -i\n").strip() == ""


def test_multiline_calc_stays_on_one_line():
    out = render("a = 2\n# hc: -m\nb = a + 1\n")
    assert out.endswith("\n\n$$\\begin{aligned} b &= a + 1 \\\\ &= 2 + 1 \\\\ &= 3 \\end{aligned}$$\n")
    assert rows("a = 2\n# hc: -m\nb = a + 1\n")[1:] == ["b &= a + 1", "&= 2 + 1", "&= 3"]


def test_params_grid_is_one_line():
    assert rows("a = 1; b = 2\nc = 3; d = 4; e = 5; f = 6; g = 7\n") == [
        "a &= 1 \\; &b &= 2 \\; &c &= 3 \\;",
        "d &= 4 \\; &e &= 5 \\; &f &= 6 \\;",
        "g &= 7 \\;",
    ]


def test_block_body_is_quoted():
    assert render("a = 2\nif a > 1:\n    b = 1\nc = 3\n") == (
        "$$\\begin{aligned} a &= 2 \\end{aligned}$$\n\n"
        "Since $\\bigl(a \\gt 1\\bigr) \\rightarrow \\bigl(2 \\gt 1\\bigr)$ is True:\n\n"
        "> $$\\begin{aligned} b &= 1 \\end{aligned}$$\n\n"
        "$$\\begin{aligned} c &= 3 \\end{aligned}$$\n"
    )


def test_nested_blocks_do_not_lazily_continue():
    # depth 2 -> depth 1 -> depth 0: a '> text' line directly after a
    # '> > text' line would be absorbed into the inner quote.
    out = render("a = 1\nif a > 0:\n    if a > 0:\n        b = 1\n    c = 2\nd = 3\n")
    assert "> > $$\\begin{aligned} b &= 1 \\end{aligned}$$\n>\n> $$" in out
    math = [(depth, content[18:24]) for depth, content in paragraph_depths(out)
            if content.startswith("$$")]
    assert math == [(0, "a &= 1"), (2, "b &= 1"), (1, "c &= 2"), (0, "d &= 3")]


def test_quoted_body_paragraphs_stay_in_one_quote():
    out = render("a = 1\nif a > 0:\n    # text\n\n    b = 2\n")
    assert out.endswith("> text\n>\n> $$\\begin{aligned} b &= 2 \\end{aligned}$$\n")
    tokens = [token.type for token in MarkdownIt().parse(out)]
    assert tokens.count("blockquote_open") == 1


def test_line_break_is_one_spacer_paragraph():
    assert render("a = 1\n# hc: -b\nb = 2\n") == (
        "$$\\begin{aligned} a &= 1 \\end{aligned}$$\n\n&nbsp;\n\n"
        "$$\\begin{aligned} b &= 2 \\end{aligned}$$\n"
    )


def test_line_break_inside_quote_is_quoted():
    out = render("a = 1\nif a > 0:\n    b = 1\n    # hc: -b\n    c = 2\n")
    assert out.count("&nbsp;") == 1
    assert "\n>\n> &nbsp;\n>\n" in out


def test_output_has_no_runs_of_blank_lines(demo_output):
    assert "\n\n\n" not in demo_output


# --- Prose --------------------------------------------------------------------

def test_heading_levels():
    assert render("## Title\n### Sub *one*\n") == "# Title\n\n## Sub \\*one\\*\n"


def test_import_is_code_span():
    assert render("import math\n") == "`import math`\n"


def test_comment_line_is_escaped_paragraph():
    assert render("# 50% of a_b * c $5 <x> `code_x` [l]\n") == (
        "50% of a\\_b \\* c \\$5 \\<x\\> `code_x` \\[l\\]\n"
    )


@pytest.mark.parametrize("text, expected", [
    ("plain text.", "plain text."),
    ("a_b * c", "a\\_b \\* c"),
    ("cost $5 | <b>", "cost \\$5 \\| \\<b\\>"),
    ("# not a heading", "\\# not a heading"),
    ("`a_b` and a_b", "`a_b` and a\\_b"),
    ("odd ` tick", "odd \\` tick"),
    ("- item", "\\- item"),
    ("+ item", "\\+ item"),
    ("1. first", "1\\. first"),
    ("2) second", "2\\) second"),
    ("a - b", "a - b"),
    ("'quoted' \"text\"", "'quoted' \"text\""),
])
def test_markdown_prose(text, expected):
    assert markdown_prose(text) == expected


# --- Text inside math ---------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("mm", "\\text{mm}"),
    ("mm^4", "\\text{mm}\\hat{}\\text{4}"),
    ("{a}", "\\{\\text{a}\\}"),
    ("50% & $1", "\\text{50}\\%\\text{ }\\&\\text{ }\\$\\text{1}"),
    ("a\\b", "\\text{a}\\backslash \\text{b}"),
    ("a_b #1 ~", "\\text{a}\\_\\text{b }\\#\\text{1 }\\tilde{}"),
    ("<b>", "\\lt \\text{b}\\gt"),
])
def test_math_text(text, expected):
    assert math_text(text) == expected


def test_math_prose_backticks_become_texttt():
    assert math_prose("use `a_b` here") == "\\text{use }\\texttt{a}\\_\\texttt{b}\\text{ here}"
    assert math_prose("odd ` tick") == "\\text{odd ` tick}"


def test_inline_comment_is_escaped_math_text():
    assert rows("I = 4 # in mm^4, 50%\n")[0] == (
        "I &= 4 \\quad\\text{(in mm}\\hat{}\\text{4, 50}\\%\\text{)}"
    )


def test_calc_comment_moves_to_own_row():
    assert rows("a = 2 # Param comment\nb = a + 1 # Calc comment\n") == [
        "a &= 2 \\quad\\text{(Param comment)}",
        "b &= a + 1 = 2 + 1 = 3",
        "&\\quad\\text{(Calc comment)}",
    ]


def test_string_constants_use_straight_quotes():
    assert rows("s = 'a_b'\nd = {'k': 1}\n") == [
        "s &= \\text{\"a}\\_\\text{b\"}",
        "d &= \\{\\text{\"k\"}\\colon 1\\}",
    ]


def test_non_string_constants_render_as_latex():
    assert rows("t = True\nn = None\nx = 2e5\n") == [
        "t &= \\mathrm{True}",
        "n &= \\mathrm{None}",
        "x &= 2 \\times 10^{5}",
    ]


# --- Math compatibility -------------------------------------------------------

def test_comparisons_use_lt_gt():
    out = rows("a = 2\nb = 3\nc = a < b\nd = a > b\ne = a <= b\n")
    assert out[2] == "c &= a \\lt b = 2 \\lt 3 = \\mathrm{True}"
    assert out[3] == "d &= a \\gt b = 2 \\gt 3 = \\mathrm{False}"
    assert out[4] == "e &= a \\le b = 2 \\le 3 = \\mathrm{True}"


def test_comparison_in_block_header_uses_lt():
    assert "Since $\\bigl(a \\lt 3\\bigr)" in render("a = 2\nif a < 3:\n    b = 1\n")


def test_no_raw_angle_brackets_in_output():
    out = render("a = 2\nb = a < 3 # x < y\nif a > 1:\n    c = 1\n")
    assert "<" not in out and ">" not in out.replace("> $$", "")


def test_inverse_hyperbolic_functions_are_operatornames():
    out = rows("import math\nx = 2.5\na = math.asinh(x)\nb = math.atanh(0.5)\n")
    assert out[1].startswith("a &= \\operatorname{arcsinh}\\left(x\\right)")
    assert out[2].startswith("b &= \\operatorname{arctanh}\\left(0.5\\right)")
