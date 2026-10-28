"""
Rendering to a file: HandCalcs(...)(source, destination=path), demo(destination=)
and each renderer's to_file(). A text renderer writes its preamble, the render
and its postamble; Word and Excel save their document or workbook.
"""

import pathlib
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import (
    ASCIIRenderer,
    BaseRenderer,
    HTMLRenderer,
    LatexRenderer,
    MarkdownRenderer,
)

SOURCE = """\
## Beam
w = 5  # kN/m
L = 6  # m
M = w * L**2 / 8
M > 20  # hc: --check
"""

TEXT_RENDERERS = [ASCIIRenderer, LatexRenderer, MarkdownRenderer, HTMLRenderer]


@pytest.mark.parametrize("renderer_cls", TEXT_RENDERERS)
def test_text_file_is_preamble_render_postamble(renderer_cls, tmp_path):
    renderer = renderer_cls()
    rendered = HandCalcs(renderer)(SOURCE)
    path = HandCalcs(renderer)(SOURCE, destination=tmp_path / "calc")
    assert path == tmp_path / "calc"
    assert path.read_bytes().decode("utf-8") == (
        renderer.preamble + rendered + renderer.postamble
    )


def test_without_destination_the_render_is_returned():
    assert isinstance(HandCalcs(LatexRenderer())(SOURCE), str)


def test_destination_may_be_a_str(tmp_path):
    path = HandCalcs(ASCIIRenderer())(SOURCE, destination=str(tmp_path / "calc.txt"))
    assert isinstance(path, pathlib.Path)
    assert path.is_file()


def test_destination_with_inputs(tmp_path):
    path = HandCalcs(ASCIIRenderer())(
        SOURCE, inputs={"w": 7}, destination=tmp_path / "calc.txt"
    )
    assert "w = 7" in path.read_text(encoding="utf-8")


def test_demo_destination(tmp_path):
    path = HandCalcs(LatexRenderer()).demo(destination=tmp_path / "demo.tex")
    assert path.read_text(encoding="utf-8").endswith("\\end{document}\n")


def test_text_is_written_as_utf8_with_newlines_unchanged(tmp_path):
    path = HandCalcs(ASCIIRenderer())("α = 2\nβ = 3\n", destination=tmp_path / "a")
    assert path.read_bytes() == "α = 2\nβ = 3\n".encode("utf-8")


def test_latex_file_is_a_document(tmp_path):
    text = HandCalcs(LatexRenderer())(SOURCE, destination=tmp_path / "c.tex")
    text = text.read_text(encoding="utf-8")
    assert text.startswith("\\documentclass{article}\n")
    # \checkmark and \color in the --check mark need amssymb and xcolor.
    for package in ("amsmath", "amssymb", "xcolor"):
        assert f"\\usepackage{{{package}}}" in text
    assert text.index("\\begin{document}") < text.index("\\section*{Beam}")
    assert text.endswith("\\end{document}\n")


def test_markdown_file_has_no_latex_document():
    renderer = MarkdownRenderer()
    assert renderer.preamble == renderer.postamble == ""


def test_ascii_file_has_nothing_around_it():
    renderer = ASCIIRenderer()
    assert renderer.preamble == renderer.postamble == ""


class TagBalance(HTMLParser):
    VOID = {"meta", "br", "img", "hr", "link", "input"}

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.seen: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.seen.append(tag)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, (tag, self.stack)
        self.stack.pop()


def test_html_file_is_a_complete_page(tmp_path):
    path = HandCalcs(HTMLRenderer())(SOURCE, destination=tmp_path / "c.html")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>\n")
    parser = TagBalance()
    parser.feed(text)
    parser.close()
    assert parser.stack == []
    assert parser.seen[:3] == ["html", "head", "meta"]
    assert '<div class="handcalcs">' in text.split("<body>", 1)[1]


def test_preamble_can_be_set_on_an_instance(tmp_path):
    renderer = LatexRenderer()
    renderer.preamble = "\\documentclass{report}\n\\begin{document}\n"
    path = HandCalcs(renderer)(SOURCE, destination=tmp_path / "c.tex")
    assert path.read_text(encoding="utf-8").startswith("\\documentclass{report}\n")
    assert LatexRenderer.preamble.startswith("\\documentclass{article}")


def test_to_file_on_the_renderer(tmp_path):
    renderer = HTMLRenderer()
    path = renderer.to_file("<p>x</p>", tmp_path / "x.html")
    assert path.read_text(encoding="utf-8") == (
        renderer.preamble + "<p>x</p>" + renderer.postamble
    )


def test_base_renderer_cannot_write_its_tree(tmp_path):
    with pytest.raises(TypeError, match="Override to_file"):
        HandCalcs(BaseRenderer())(SOURCE, destination=tmp_path / "tree")
    assert not (tmp_path / "tree").exists()


EXCEL_SOURCE = """\
w = 5
L = 6
M = w * L**2 / 8
"""


def test_excel_destination_saves_the_workbook(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from handcalcs.renderers.excel import ExcelRenderer

    path = HandCalcs(ExcelRenderer())(EXCEL_SOURCE, destination=tmp_path / "c.xlsx")
    assert path == tmp_path / "c.xlsx"
    sheet = openpyxl.load_workbook(path)["Calculations"]
    formulas = [cell.value for row in sheet.iter_rows() for cell in row]
    assert any(isinstance(v, str) and v.startswith("=") for v in formulas)


def test_word_destination_saves_the_document(tmp_path):
    docx = pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    path = HandCalcs(WordRenderer())(SOURCE, destination=tmp_path / "c.docx")
    assert path == tmp_path / "c.docx"
    document = docx.Document(path)
    assert any("Beam" in paragraph.text for paragraph in document.paragraphs)


def test_word_filepath_still_saves(tmp_path):
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    target = tmp_path / "auto.docx"
    document = HandCalcs(WordRenderer(filepath=target))(SOURCE)
    assert target.is_file()
    assert hasattr(document, "paragraphs")


def find_pdflatex():
    tinytex = pathlib.Path.home() / ".TinyTeX" / "bin" / "x86_64-linux" / "pdflatex"
    return shutil.which("pdflatex") or (str(tinytex) if tinytex.exists() else None)


@pytest.mark.skipif(find_pdflatex() is None, reason="pdflatex is not installed")
def test_latex_file_compiles(tmp_path):
    path = HandCalcs(LatexRenderer()).demo(destination=tmp_path / "demo.tex")
    checks = HandCalcs(LatexRenderer())(SOURCE, destination=tmp_path / "checks.tex")
    for tex in (path, checks):
        result = subprocess.run(
            [find_pdflatex(), "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout[-2000:]


# --- @handcalc(destination=) ---


@pytest.mark.parametrize("renderer_cls", TEXT_RENDERERS)
def test_decorator_destination_writes_each_call(renderer_cls, tmp_path):
    from handcalcs import handcalc

    renderer = renderer_cls()
    destination = tmp_path / "beam"

    @handcalc(renderer, destination=destination)
    def beam(w, L):
        M = w * L**2 / 8
        return M

    rendered = handcalc(renderer)(beam.__wrapped__)(5, 6)[1]
    assert beam(5, 6) == (22.5, destination)
    assert destination.read_text(encoding="utf-8") == (
        renderer.preamble + rendered + renderer.postamble
    )
    # The next call writes over the file.
    beam(4, 6)
    assert "18" in destination.read_text(encoding="utf-8")


def test_decorator_without_destination_returns_the_render():
    from handcalcs import handcalc

    @handcalc(ASCIIRenderer())
    def double(a):
        b = a * 2
        return b

    assert double(2) == (4, "b = a * 2 = 2 * 2 = 4\n")


def test_decorator_destination_saves_word_and_excel(tmp_path):
    docx = pytest.importorskip("docx")
    openpyxl = pytest.importorskip("openpyxl")
    from handcalcs import handcalc
    from handcalcs.renderers.excel import ExcelRenderer
    from handcalcs.renderers.word import WordRenderer

    def beam():
        w = 5
        L = 6
        M = w * L**2 / 8
        return M

    word = handcalc(WordRenderer(), destination=tmp_path / "beam.docx")(beam)
    excel = handcalc(ExcelRenderer(), destination=tmp_path / "beam.xlsx")(beam)
    assert word() == (22.5, tmp_path / "beam.docx")
    assert excel() == (22.5, tmp_path / "beam.xlsx")
    assert "M" in "".join(docx.Document(tmp_path / "beam.docx").element.body.itertext())
    sheet = openpyxl.load_workbook(tmp_path / "beam.xlsx")["Calculations"]
    assert any(cell.value == "=w*L^2/8" for row in sheet.iter_rows() for cell in row)
