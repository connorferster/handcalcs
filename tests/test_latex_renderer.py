"""
Tests for the LatexRenderer, run through the full HandCalcs pipeline
(source -> parser -> HcSequence -> LatexRenderer -> complete()).

- Golden tests: the rendered demo is compared, section by section, against
  ``tests/golden/latex_demo.tex``. After an intended change to the output,
  regenerate it with ``HANDCALCS_UPDATE_GOLDEN=1 uv run pytest tests/test_latex_renderer.py``
  and review the diff.
- Focused tests pin the individual fixes from latex_implementation_plan.md.
- A compile test builds the demo with pdflatex (skipped when it is not installed).
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers.latex import LatexRenderer, latex_identifier, latex_prose

GOLDEN = pathlib.Path(__file__).parent / "golden" / "latex_demo.tex"
UPDATE_GOLDEN = os.environ.get("HANDCALCS_UPDATE_GOLDEN") == "1"


def render(source: str) -> str:
    return HandCalcs(renderer=LatexRenderer())(source)


def rows(source: str) -> list[str]:
    """The rows of every aligned math group in the output, stripped of ``\\\\``."""
    return [
        line.removesuffix(" \\\\")
        for line in render(source).splitlines()
        if "&" in line
    ]


def sections(text: str) -> dict[str, str]:
    """Split a rendered demo into its preamble and ``\\subsection*`` sections."""
    parts = re.split(r"(?=^\\subsection\*\{)", text, flags=re.MULTILINE)
    named = {}
    for part in parts:
        heading = re.match(r"\\(?:sub)?section\*\{([^}]*)\}", part)
        named[heading.group(1) if heading else "preamble"] = part
    return named


@pytest.fixture(scope="module")
def demo_output() -> str:
    output = HandCalcs(renderer=LatexRenderer()).demo()
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


def find_pdflatex() -> str | None:
    found = shutil.which("pdflatex")
    if found:
        return found
    tinytex = pathlib.Path.home() / ".TinyTeX" / "bin" / "x86_64-linux" / "pdflatex"
    return str(tinytex) if tinytex.exists() else None


@pytest.mark.skipif(find_pdflatex() is None, reason="pdflatex is not installed")
def test_demo_compiles_with_pdflatex(demo_output, tmp_path):
    tex = tmp_path / "demo.tex"
    tex.write_text(
        "\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n"
        f"{demo_output}\\end{{document}}\n"
    )
    result = subprocess.run(
        [find_pdflatex(), "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    problems = [
        line for line in result.stdout.splitlines()
        if line.startswith("!") or "Warning" in line
    ]
    assert result.returncode == 0 and not problems, "\n".join(problems)


# --- Output structure ---------------------------------------------------------

def test_calcs_block_is_one_aligned_group_without_trailing_row_break():
    assert render("a = 1\nb = 2\n") == (
        "\\medskip\n\\noindent$\\displaystyle\n\\begin{aligned}[t]\n"
        "a &= 1 \\\\\nb &= 2\n\\end{aligned}$\n\n\\medskip\n"
    )


def test_all_ignored_calcs_block_emits_no_group():  # 9
    assert render("acc = [] # hc: -i\n").strip() == ""


def test_alignment_on_first_assign_only():  # 10
    assert rows("a = 2\nb = a + 1\n")[1] == "b &= a + 1 = 2 + 1 = 3"


def test_params_grid_is_aligned_and_ragged():  # 12
    assert rows("a = 1; b = 2\nc = 3; d = 4; e = 5; f = 6; g = 7\n") == [
        "a &= 1 &\\qquad b &= 2 &\\qquad c &= 3",
        "d &= 4 &\\qquad e &= 5 &\\qquad f &= 6",
        "g &= 7",
    ]


def test_multiline_calc_aligns_each_row():  # 13
    assert rows("a = 2\n# hc: -m\nb = a + 1\n")[1:] == [
        "b &= a + 1",
        "&= 2 + 1",
        "&= 3",
    ]


def test_text_lines_are_escaped_paragraphs():  # 6, 27
    out = render("# 50% of a_b & c\nimport math\n")
    assert "\\noindent 50\\% of a\\_b \\& c" in out
    assert "\\noindent \\texttt{import math}" in out


def test_if_header_math_is_delimited():  # 7
    out = render("a = 2\nif a > 1:\n    b = 1\n")
    assert "Since $\\left(a > 1\\right) \\rightarrow \\left(2 > 1\\right)$ is True:" in out


# --- Operators ----------------------------------------------------------------

def test_modulo_is_bmod():  # 1
    assert rows("a = 7\nb = 3\nc = a % b\n")[2] == "c &= a \\bmod b = 7 \\bmod 3 = 1"


def test_power_braces_compound_exponent():  # 2
    assert rows("a = 7\nb = 3\nd = a ** (b + 1)\n")[2] == (
        "d &= a^{b + 1} = 7^{3 + 1} = 2401"
    )


def test_negative_power_base_is_parenthesised():  # 3
    assert rows("f = (-3) ** 2\n")[0] == (
        "f &= \\left(-3\\right)^{2} = 9"
    )
    assert rows("b = -2\nc = b ** 2\n")[1] == "c &= b^{2} = \\left(-2\\right)^{2} = 4"


def test_division_and_floor_division_are_fractions():  # 11
    assert rows("a = 6\nb = 3\nc = (a + 1) / b\n")[2].startswith(
        "c &= \\frac{a + 1}{b} = \\frac{6 + 1}{3}"
    )
    assert rows("a = 7\nb = 3\ng = a // b\n")[2] == (
        "g &= \\left\\lfloor\\frac{a}{b}\\right\\rfloor"
        " = \\left\\lfloor\\frac{7}{3}\\right\\rfloor = 2"
    )


def test_comparisons():  # 20, 21
    out = rows("a = 2\nb = 3\nt = a == b\nu = a <= b\n")
    assert out[2] == "t &= a == b = 2 == 3 = \\mathrm{False}"
    assert out[3] == "u &= a \\le b = 2 \\le 3 = \\mathrm{True}"


def test_word_operators():  # 15, 16
    out = rows("a = 1\nb = [1]\nc = a in b and not (a < 0)\n")
    assert out[2].startswith(
        "c &= a \\in b \\;\\mathrm{and}\\; \\mathrm{not}\\;\\left(a < 0\\right)"
    )


# --- Values -------------------------------------------------------------------

def test_dict_and_set_braces_are_escaped():  # 4
    assert rows("s = {1, 2}\nd = {'k': 1}\n") == [
        "s &= \\{1, 2\\}",
        "d &= \\{\\text{``k''}\\colon 1\\}",
    ]


def test_inline_comment_is_escaped_text():  # 5
    assert rows("I = 4 # in mm^4\n")[0] == (
        "I &= 4 \\quad\\text{(in mm\\textasciicircum{}4)}"
    )


def test_string_bool_none_and_complex_constants():  # 17, 19, 25
    assert rows("s = 'a_b'\nt = True\nn = None\nz = 3+4j\n") == [
        "s &= \\text{``a\\_b''}",
        "t &= \\mathrm{True}",
        "n &= \\mathrm{None}",
        "z &= 3 + 4j",  # parsed as the BinOp 3 + 4j; repeated columns collapse
    ]
    assert rows("z = 4j - 3\n")[0].endswith("= -3 + 4j")


@pytest.mark.parametrize("source, expected", [
    ("x = 2e5\n", "x &= 2 \\times 10^{5}"),
    ("x = 1e-7\n", "x &= 10^{-7}"),
    ("x = -10.42314 # hc: -f .3e\n", "x &= -1.042 \\times 10^{1}"),
    ("x = 0.5\n", "x &= 0.5"),
])
def test_scientific_notation(source, expected):  # 18
    assert rows(source)[0] == expected


# --- Names --------------------------------------------------------------------

@pytest.mark.parametrize("identifier, expected", [
    ("x", "x"),
    ("x_1", "x_{1}"),
    ("x_a_b", "x_{a_{b}}"),
    ("class_section", "\\mathrm{class}_{\\mathrm{section}}"),
    ("rate_12", "\\mathrm{rate}_{12}"),
    ("omega_2", "\\omega_{2}"),
    ("alpha_Rho", "\\alpha_{\\mathrm{P}}"),
    ("Gamma", "\\Gamma"),
    ("Alpha", "\\mathrm{A}"),
    ("Eta_max", "\\mathrm{H}_{\\mathrm{max}}"),
    ("omicron", "o"),
    ("lamb", "\\lambda"),
    ("x__y", "\\mathrm{x\\ y}"),
    ("a___b", "\\mathrm{a\\_b}"),
])
def test_latex_identifier(identifier, expected):  # 8, 23
    assert latex_identifier(identifier) == expected


def test_latex_identifier_is_idempotent():
    for identifier in ("x_1", "class_section", "omega_2", "Alpha"):
        once = latex_identifier(identifier)
        assert latex_identifier(once) == once


def test_math_constants_drop_namespace():  # 14
    assert rows("import math\nr = 2\na = math.pi * r\nz = math.inf\n")[1:] == [
        "a &= \\pi \\cdot r = 3.1416 \\cdot 2 = 6.2832",
        "z &= \\infty",
    ]


def test_repeated_value_columns_collapse():
    assert rows("import math\ny = 3\nq = y\nw = math.pi\nv = 2 + 3\n")[1:] == [
        "q &= y = 3",
        "w &= \\pi = 3.1416",
        "v &= 2 + 3 = 5",
    ]


def test_math_functions_drop_namespace():
    out = rows("import math\nx = 2.5\na = math.floor(x)\nb = math.sqrt(x)\nc = math.sin(x)\n")
    assert out[1].startswith("a &= \\lfloor x\\rfloor = \\lfloor 2.5\\rfloor")
    assert out[2].startswith("b &= \\sqrt{x} = \\sqrt{2.5}")
    assert out[3].startswith("c &= \\sin\\left(x\\right) = \\sin\\left(2.5\\right)")


def test_user_function_and_method_names():  # 24, 26
    out = rows("def my_func(t):\n    return t\nw = my_func(2)\nacc = []\nacc.append(w)\n")
    assert out[0] == "w &= \\operatorname{my\\_func}\\left(2\\right) = 2"
    assert out[-1] == (
        "\\mathrm{acc}.\\mathrm{append}\\left(w\\right)"
        " &= \\mathrm{acc}.\\mathrm{append}\\left(2\\right)"
    )


# --- Prose --------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("The `and`/`or` ops", "The \\texttt{and}/\\texttt{or} ops"),
    ("variables 'a' and 'b'", "variables `a' and `b'"),
    ('say "hi"', "say ``hi''"),
    ("it's 50% `a_b`", "it's 50\\% \\texttt{a\\_b}"),
    ("odd ` tick", "odd \\textasciigrave{} tick"),
])
def test_latex_prose(text, expected):
    assert latex_prose(text) == expected
