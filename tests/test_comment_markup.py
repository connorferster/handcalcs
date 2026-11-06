"""
Light markup in comments (headings, comment lines, inline comments): `code`,
**bold** and *italic* in every renderer, and $math$ in the LaTeX and Markdown
renderers (#350), which ``comment_math=False`` turns off.
"""

import io
import zipfile

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers.ascii import ASCIIRenderer
from handcalcs.renderers.html import HTMLRenderer, html_prose
from handcalcs.renderers.latex import LatexRenderer, latex_prose
from handcalcs.renderers.markdown import MarkdownRenderer, markdown_prose, math_prose
from handcalcs.renderers.prose import plain_prose, prose_spans


def spans(text: str, math: bool = True) -> list[tuple[str, str]]:
    return [(span.kind, span.text) for span in prose_spans(text, math=math)]


# --- The tokenizer ------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("plain text", [("text", "plain text")]),
        ("**Utilization above 90%.** Confirm", [("strong", "Utilization above 90%."), ("text", " Confirm")]),
        ("use *only* if", [("text", "use "), ("em", "only"), ("text", " if")]),
        ("(*x*) and **y**.", [("text", "("), ("em", "x"), ("text", ") and "), ("strong", "y"), ("text", ".")]),
        ("`a_b` and `c", [("code", "a_b"), ("text", " and `c")]),
        ("`*not em*`", [("code", "*not em*")]),
        # Formulas are not emphasis.
        ("w*L**2/8", [("text", "w*L**2/8")]),
        ("a * b * c", [("text", "a * b * c")]),
        ("x**2 + y**2", [("text", "x**2 + y**2")]),
        ("2 ** 3", [("text", "2 ** 3")]),
        ("***x***", [("text", "***x***")]),
        ("a_b_c", [("text", "a_b_c")]),
        ("\\*x*", [("text", "*x*")]),
        # Math.
        ("$x^y$", [("math", "x^y")]),
        ("in $\\sigma_x$ units", [("text", "in "), ("math", "\\sigma_x"), ("text", " units")]),
        ("$$a$$ and $b$", [("math", "a"), ("text", " and "), ("math", "b")]),
        ("`$x$`", [("code", "$x$")]),
        # Prices are not math.
        ("costs $5 to $10", [("text", "costs $5 to $10")]),
        ("between $5-$6", [("text", "between $5-$6")]),
        ("$ 5 $", [("text", "$ 5 $")]),
        ("\\$x$", [("text", "$x$")]),
        ("$$", [("text", "$$")]),
        # Unbalanced braces are text.
        ("$\\frac{a$", [("text", "$\\frac{a$")]),
        ("$a}$", [("text", "$a}$")]),
    ],
)
def test_prose_spans(text, expected):
    assert spans(text) == expected


def test_math_only_when_asked():
    assert spans("$x^y$ and \\$", math=False) == [("text", "$x^y$ and \\$")]


def test_plain_prose():
    assert plain_prose(prose_spans("**a** `b` $c$ *d*", math=True)) == "a `b` $c$ d"


# --- LaTeX --------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("**bold** and *it*", "\\textbf{bold} and \\emph{it}"),
        ("`a_b` x", "\\texttt{a\\_b} x"),
        ("$x^y$ 50%", "$x^y$ 50\\%"),
        ("costs $5", "costs \\$5"),
    ],
)
def test_latex_prose(text, expected):
    assert latex_prose(text, math=True) == expected


def test_latex_prose_in_math_uses_parens():
    # A "$" in an inline comment would end the "$"-delimited math group for MathJax.
    assert latex_prose("in $x^y$", math=True, in_math=True) == "in \\(x^y\\)"


def test_latex_renderer():
    rendered = HandCalcs(LatexRenderer())(
        "## Load *case*\n# The **factored** load $w_f$\nw_f = 2  # in $\\mathrm{kN/m}$\n"
    )
    assert "\\section*{Load \\emph{case}}" in rendered
    assert "\\noindent The \\textbf{factored} load $w_f$" in rendered
    assert "w_{f} &= 2 \\quad\\text{(in \\(\\mathrm{kN/m}\\))}" in rendered


def test_latex_comment_math_off():
    rendered = HandCalcs(LatexRenderer(comment_math=False))("x = 2  # $y$ **b**\n")
    assert "\\text{(\\$y\\$ \\textbf{b})}" in rendered


def test_latex_comment_math_class_attribute():
    class NoMath(LatexRenderer):
        COMMENT_MATH = False

    assert NoMath().comment_math is False
    assert NoMath(comment_math=True).comment_math is True
    assert LatexRenderer().comment_math is True


# --- Markdown -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("**Utilization is above 90%.** Confirm.", "**Utilization is above 90%.** Confirm."),
        ("*a_b* and a_b", "*a\\_b* and a\\_b"),
        ("$x_1$ and x_1", "$x_1$ and x\\_1"),
        ("w*L**2/8", "w\\*L\\*\\*2/8"),
        ("costs $5 to $10", "costs \\$5 to \\$10"),
        ("odd ` tick", "odd \\` tick"),
    ],
)
def test_markdown_prose(text, expected):
    assert markdown_prose(text, math=True) == expected


def test_math_prose_has_no_dollar():
    # Inside a "$$" math group: the math is set directly, with no "$".
    assert math_prose("(stress $\\sigma < 5$ **ok**)", math=True) == (
        "\\text{(stress }{\\sigma \\lt  5}\\text{ }\\textbf{ok}\\text{)}"
    )


def test_markdown_renderer():
    rendered = HandCalcs(MarkdownRenderer())(
        "# hc: --show\n# **Utilization is above 90%.** Check $L_e$.\nx = 2  # in $x^2$\n"
    )
    assert "**Utilization is above 90%.** Check $L_e$." in rendered
    assert "x &= 2 \\quad\\text{(in }{x^2}\\text{)}" in rendered


def test_markdown_comment_math_off():
    rendered = HandCalcs(MarkdownRenderer(comment_math=False))("# $x$ **b**\nx = 1\n")
    assert "\\$x\\$ **b**" in rendered


# --- HTML, ASCII, Word and Excel: emphasis and code, no math ------------------


def test_html_prose():
    assert html_prose("**a** *b* `c` <d> $e$") == (
        "<strong>a</strong> <em>b</em> <code>c</code> &lt;d&gt; $e$"
    )


def test_html_renderer():
    rendered = HandCalcs(HTMLRenderer())("## A *b*\n# Some **bold**\nx = 1  # *it*\n")
    assert "<h1>A <em>b</em></h1>" in rendered
    assert '<p class="hc-comment">Some <strong>bold</strong></p>' in rendered
    assert '<span class="hc-note">(<em>it</em>)</span>' in rendered


def test_ascii_keeps_the_markers():
    source = "# Some **bold** and $x$\nx = 1  # *it*\n"
    assert HandCalcs(ASCIIRenderer())(source) == "Some **bold** and $x$\nx = 1 (*it*)\n"


def test_word_runs():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    document = HandCalcs(WordRenderer())("## A *b*\n# Some **bold**\nx = 1  # `c`\n")
    buffer = io.BytesIO()
    document.save(buffer)
    xml = zipfile.ZipFile(buffer).read("word/document.xml").decode()
    assert "<w:b/>" in xml and "<w:i/>" in xml
    assert '<w:rFonts w:ascii="Consolas"' in xml
    assert "**" not in xml and "`" not in xml


def test_excel_rich_text():
    openpyxl = pytest.importorskip("openpyxl")
    from handcalcs.renderers.excel import ExcelRenderer

    workbook = HandCalcs(ExcelRenderer())("## A *b*\n# Some **bold**\nx = 1  # *it*\n")
    sheet = openpyxl.load_workbook(io.BytesIO(workbook.to_bytes()), rich_text=True).active
    values = [str(cell.value) for row in sheet.iter_rows() for cell in row if cell.value]
    assert "A b" in values and "Some bold" in values
    assert not any("*" in value for value in values)
