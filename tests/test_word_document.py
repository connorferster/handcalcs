"""
Tests for the Word renderer's document layout (#222, step 4): calc blocks as
equation arrays (or one equation per row), params tables, prose, headings and
nested blocks. Each test renders a source, then reads the python-docx
``Document``'s body back.
"""

import pytest

docx = pytest.importorskip("docx")

from docx.oxml.ns import qn

from handcalcs import HandCalcs
from handcalcs.renderers.base import BaseRenderer
from handcalcs.renderers.word import WordRenderer, omml
from handcalcs.renderers.word.document import Heading, ParamsTable

M = f"{{{omml.M_NS}}}"


def render(source: str, **options):
    return HandCalcs(renderer=WordRenderer(**options))(source)


def math_text(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{M}t"))


def eq_rows(paragraph) -> list[str]:
    """The text of each row of a paragraph's equation array."""
    return [math_text(row) for row in paragraph.findall(f".//{M}eqArr/{M}e")]


def indent(paragraph) -> int:
    ind = paragraph.find(f"{qn('w:pPr')}/{qn('w:ind')}")
    return int(ind.get(qn("w:left"))) if ind is not None else 0


def body(document) -> list:
    """The body's paragraphs and tables (without the section properties)."""
    return [el for el in document.element.body if el.tag != qn("w:sectPr")]


def math_paragraphs(document) -> list:
    return [el for el in body(document) if el.find(f"{M}oMathPara") is not None]


# --- calc blocks: the "aligned" layout ---------------------------------------


def test_complete_returns_a_document():
    document = render("a = 2\n")
    assert isinstance(document, docx.document.Document)


def test_calc_block_is_one_equation_array():
    document = render("a = 2\nb = 3\nc = a * b\n")
    (paragraph,) = math_paragraphs(document)
    assert eq_rows(paragraph) == ["a&=2", "b&=3", "c&=a⋅b=2⋅3=6"]
    jc = paragraph.find(f"{M}oMathPara/{M}oMathParaPr/{M}jc")
    assert jc.get(f"{M}val") == "left"


def test_alignment_point_is_its_own_run():
    document = render("a = 2\n")
    (paragraph,) = math_paragraphs(document)
    row = paragraph.find(f".//{M}eqArr/{M}e")
    runs = [math_text(run) for run in row.findall(f"{M}r")]
    assert runs == ["a", "&", "=", "2"]


def test_comment_stays_on_its_row_with_substitutions():
    document = render("a = 2\nb = a * 3  # note\n")
    (paragraph,) = math_paragraphs(document)
    assert eq_rows(paragraph) == ["a&=2", "b&=a⋅3=2⋅3=6\u2003(note)"]


def test_comment_stays_on_a_short_row():
    document = render("a = 2  # note\n")
    (paragraph,) = math_paragraphs(document)
    assert eq_rows(paragraph) == ["a&=2\u2003(note)"]


def test_multiline_calc_rows():
    document = render("a = 2\n# hc: -m\nb = a * 3\n")
    rows = [row for p in math_paragraphs(document) for row in eq_rows(p)]
    assert rows[-3:] == ["b&=a⋅3", "&=2⋅3", "&=6"]


def test_continuation_rows_start_with_an_em_space():
    document = render("a = 2\nb = a + \\\n    a * 3\n")
    rows = [row for p in math_paragraphs(document) for row in eq_rows(p)]
    assert rows[1:] == ["b&=a+", "&\u2003a⋅3", "&=2+", "&\u20032⋅3", "&=8"]


def test_ignored_lines_make_no_rows():
    document = render("a = 2  # hc: -i\nb = 3\n")
    (paragraph,) = math_paragraphs(document)
    assert eq_rows(paragraph) == ["b&=3"]


# --- the "lines" layout --------------------------------------------------------


def test_lines_layout_is_one_equation_per_row():
    document = render("a = 2\n# hc: -m\nb = a * 3\n", layout="lines")
    paragraphs = math_paragraphs(document)
    assert [math_text(p) for p in paragraphs] == ["a=2", "b=a⋅3", "=2⋅3", "=6"]
    assert [indent(p) for p in paragraphs] == [0, 0, 360, 360]
    assert not document.element.body.findall(f".//{M}eqArr")


def test_layout_comment_applies_to_the_calcs_after_it():
    source = 'a = 2\n# hc: layout = "lines"\nb = 3\nc = 4\n'
    document = render(source)
    arrays = document.element.body.findall(f".//{M}eqArr")
    assert [math_text(arr) for arr in arrays] == ["a&=2"]
    assert [math_text(p) for p in math_paragraphs(document)][1:] == ["b=3", "c=4"]


def test_unknown_layout_is_an_error():
    with pytest.raises(ValueError, match="layout"):
        WordRenderer(layout="table")
    with pytest.raises(ValueError, match="layout"):
        render('# hc: layout = "table"\na = 2\n')


# --- params, prose and blocks ----------------------------------------------------


def test_params_grid_is_a_borderless_table():
    document = render("b = 300; d = 500; f_c = 30\nt = 2; x = 1\n")
    (table,) = document.tables
    assert len(table.rows) == 2 and len(table.columns) == 3
    cells = [math_text(cell._tc) for row in table.rows for cell in row.cells]
    assert cells == ["b=300", "d=500", "fc=30", "t=2", "x=1", ""]
    assert table.style is None or "Grid" not in table.style.name


def test_heading_comment_and_import():
    document = render("## Loads\n# The {{ 'dead' }} load\n# in kN\nimport math\n")
    heading, prose, code = document.paragraphs
    assert (heading.style.name, heading.text) == ("Heading 1", "Loads")
    assert prose.text == "The dead load in kN"
    assert code.text == "import math"
    assert code.runs[0].style.name == "HC Code"


def test_line_break_is_an_empty_paragraph():
    document = render("a = 2\n# hc: -b\nb = 3\n")
    assert [p.text for p in document.paragraphs] == ["", "", ""]
    assert len(math_paragraphs(document)) == 2


def test_if_block_header_and_indented_body():
    source = "a = 2\nif a > 1:\n    b = 3\n    if b > 2:\n        c = 4\n"
    document = render(source)
    headers = [p for p in body(document) if "Since" in "".join(p.itertext())]
    assert len(headers) == 2
    first = headers[0]
    assert first.find(f"{M}oMath") is not None
    assert "".join(t.text for t in first.iter(qn("w:t"))) == "Since  is True:"
    assert math_text(first) == "a>1→2>1"
    assert [indent(h) for h in headers] == [0, 720]
    assert [(eq_rows(p), indent(p)) for p in math_paragraphs(document)] == [
        (["a&=2"], 0),
        (["b&=3"], 720),
        (["c&=4"], 1440),
    ]


def test_nested_params_table_is_indented():
    document = render("a = 2\nif a > 1:\n    b = 3; c = 4\n")
    (table,) = document.tables
    ind = table._tbl.tblPr.find(qn("w:tblInd"))
    assert ind.get(qn("w:w")) == "720"


def test_for_block_header():
    document = render("total = 0\nfor i in [1, 2]:\n    total = total + i\n")
    header = next(p for p in body(document) if "Iterating" in "".join(p.itertext()))
    assert len(header.findall(f"{M}oMath")) == 2


def test_filepath_saves_the_document(tmp_path):
    path = tmp_path / "calc.docx"
    render("## Check\na = 2\nb = a * 3\n", filepath=path)
    reopened = docx.Document(str(path))
    assert reopened.paragraphs[0].style.name == "Heading 1"
    (paragraph,) = math_paragraphs(reopened)
    assert eq_rows(paragraph) == ["a&=2", "b&=a⋅3=2⋅3=6"]


@pytest.mark.parametrize("layout", ["aligned", "lines"])
def test_demo_renders(layout, tmp_path):
    path = tmp_path / "demo.docx"
    HandCalcs(renderer=WordRenderer(filepath=path, layout=layout)).demo()
    reopened = docx.Document(str(path))
    assert math_paragraphs(reopened)
    assert reopened.tables


# --- styles, templates and documents ---------------------------------------------


def test_renderer_styles():
    document = render("import math\na = 2\n")
    styles = document.styles
    assert styles["HC Code"].font.name == "Consolas"
    math_style = styles["HC Math"]
    assert math_style.base_style.name == "Normal"
    assert math_style.element.find(f".//{qn('w:contextualSpacing')}") is not None
    (paragraph,) = [p for p in document.paragraphs if p._p in math_paragraphs(document)]
    assert paragraph.style.name == "HC Math"


def make_template(path, **styles):
    """A template with a line of content and, optionally, its own HC Math style."""
    from docx.enum.style import WD_STYLE_TYPE
    from docx.shared import Pt

    template = docx.Document()
    template.add_paragraph("Company letterhead")
    if "math_size" in styles:
        style = template.styles.add_style("HC Math", WD_STYLE_TYPE.PARAGRAPH)
        style.font.size = Pt(styles["math_size"])
    template.save(str(path))
    return path


def test_template_content_and_styles_are_kept(tmp_path):
    template = make_template(tmp_path / "company.docx", math_size=14)
    renderer = WordRenderer(template=template)
    first = HandCalcs(renderer=renderer)("a = 2\n")
    second = HandCalcs(renderer=renderer)("b = 3\n")
    for document in (first, second):
        assert document.paragraphs[0].text == "Company letterhead"
        assert document.styles["HC Math"].font.size.pt == 14
        assert len(math_paragraphs(document)) == 1


def test_document_option_appends_calcs():
    report = docx.Document()
    report.add_heading("Report", level=0)
    calc = HandCalcs(renderer=WordRenderer(document=report))
    assert calc("a = 2\n") is report
    calc("b = 3\n")
    assert [eq_rows(p) for p in math_paragraphs(report)] == [["a&=2"], ["b&=3"]]
    assert report.paragraphs[0].text == "Report"


def test_template_and_document_options_are_checked(tmp_path):
    with pytest.raises(ValueError, match="not both"):
        WordRenderer(
            template=make_template(tmp_path / "t.docx"), document=docx.Document()
        )
    with pytest.raises(FileNotFoundError):
        WordRenderer(template=tmp_path / "missing.docx")


def test_missing_heading_style_falls_back_to_bold(tmp_path):
    template = docx.Document()
    heading = template.styles["Heading 1"].element
    heading.getparent().remove(heading)
    path = tmp_path / "plain.docx"
    template.save(str(path))
    with pytest.warns(UserWarning, match="Heading 1"):
        document = HandCalcs(renderer=WordRenderer(template=path))("## Loads\na = 2\n")
    paragraph = document.paragraphs[0]
    assert paragraph.text == "Loads" and paragraph.runs[0].bold


def demo_items(item_type) -> int:
    class TreeWordRenderer(WordRenderer):
        complete = BaseRenderer.complete

    def count(item) -> int:
        if isinstance(item, item_type):
            return 1
        if isinstance(item, list):
            return sum(count(child) for child in item)
        return 0

    return count(HandCalcs(renderer=TreeWordRenderer()).demo())


def test_demo_structure_matches_the_render_tree():
    document = HandCalcs(renderer=WordRenderer()).demo()
    headings = [p for p in document.paragraphs if p.style.name.startswith("Heading")]
    assert len(headings) == demo_items(Heading)
    assert len(document.tables) == demo_items(ParamsTable)
    rows = document.element.body.findall(f".//{M}eqArr/{M}e")
    assert len(rows) > 20
    for row in rows:
        marks = [run for run in row.findall(f"{M}r") if math_text(run) == "&"]
        assert len(marks) == 1, math_text(row)


def test_demo_lines_layout_has_no_alignment_marks():
    document = HandCalcs(renderer=WordRenderer(layout="lines")).demo()
    runs = document.element.body.findall(f".//{M}r")
    assert runs and not [run for run in runs if math_text(run) == "&"]


# --- long equations: keeping within the page ----------------------------------

LONG = (
    "first_val = 1.2345\nsecond_val = 2.3456\nthird_val = 3.4567\n"
    "result_val = (first_val * second_val + third_val ** 2) / (first_val + second_val)"
    " + first_val * third_val - second_val / third_val\n"
)


def sizes(paragraph) -> set[int]:
    return {int(sz.get(qn("w:val"))) for sz in paragraph.iter(qn("w:sz"))}


def test_long_row_is_split_one_step_per_row():
    # Too wide for the page on one row: the symbolic, numeric and result steps
    # each get a row, aligned on their "=".
    document = render(LONG)
    (paragraph,) = math_paragraphs(document)
    rows = eq_rows(paragraph)
    assert len(rows) == 6
    assert rows[3].startswith("resultval&=") and rows[3].count("=") == 1
    assert all(row.startswith("&=") and row.count("=") == 1 for row in rows[4:])


def test_short_rows_are_not_split():
    document = render("a = 2\nb = a * 3\n")
    (paragraph,) = math_paragraphs(document)
    assert eq_rows(paragraph) == ["a&=2", "b&=a⋅3=2⋅3=6"]


def test_wide_page_keeps_the_row_whole():
    from docx.shared import Inches

    document = docx.Document()
    document.sections[0].page_width = Inches(40)
    render(LONG, document=document)
    (paragraph,) = math_paragraphs(document)
    assert len(eq_rows(paragraph)) == 4


def test_row_still_too_wide_is_its_own_smaller_equation():
    # One step that cannot be split (a long sum) is set apart, in a smaller
    # font, but not below MIN_MATH_SCALE of 11 pt.
    terms = " + ".join(f"value_number_{k}" for k in range(12))
    source = "".join(f"value_number_{k} = {k}\n" for k in range(12)) + f"total = {terms}\n"
    document = render(source)
    paragraphs = math_paragraphs(document)
    assert len(paragraphs) > 1
    assert not sizes(paragraphs[0])
    smaller = [sizes(p) for p in paragraphs if sizes(p)]
    assert smaller and all(size >= round(22 * 0.6) for s in smaller for size in s)


def test_lines_layout_splits_long_rows_too():
    document = render(LONG, layout="lines")
    texts = [math_text(p) for p in math_paragraphs(document)]
    assert len(texts) == 6


def test_wide_g_grid_reflows_into_fewer_columns():
    cells = "".join(
        f"parameter_with_a_long_name_{k} = {k}.12345  # a comment about it\n"
        for k in range(6)
    )
    document = render("# hc: -g -c 3\n" + cells)
    (table,) = document.tables
    assert len(table.columns) < 3


def test_semicolon_grid_keeps_its_rows():
    row = "; ".join(f"parameter_with_a_long_name_{k} = {k}.12345" for k in range(4))
    document = render(row + "\n")
    (table,) = document.tables
    assert len(table.columns) == 4


def test_narrow_g_grid_keeps_its_columns():
    document = render("# hc: -g -c 3\na = 1\nb = 2\nc = 3\nd = 4\n")
    (table,) = document.tables
    assert len(table.columns) == 3


def test_text_width_follows_the_page_and_the_style():
    from docx.shared import Pt
    from handcalcs.renderers.word.document import DocumentWriter

    document = docx.Document()
    writer = DocumentWriter(document)
    assert writer.font_size() == 11
    assert writer.max_math_width() == pytest.approx(432 / 11)
    assert writer.max_math_width(depth=1) == pytest.approx((432 - 36) / 11)
    document.styles["HC Math"].font.size = Pt(12)
    assert writer.max_math_width() == pytest.approx(432 / 12)
