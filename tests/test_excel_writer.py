"""
Tests for the XlsxWriter backend: each workbook is read back with openpyxl to
check layout, defined names, formulas, cached values, formats and merges.
"""
import io
import pytest

openpyxl = pytest.importorskip("openpyxl")
xlsxwriter = pytest.importorskip("xlsxwriter")

from handcalcs import HandCalcs
from handcalcs.renderers.excel import ExcelRenderer, ExcelWorkbook
from handcalcs.renderers.excel.writer import HEADING_SIZES

SOURCE = '''"""Quadratic roots"""
from math import sqrt
## Roots
### Larger root
# Solve a*x**2 + b*x + c = 0 for the larger root. This paragraph is long
# enough to wrap across the merged cells of the sheet, several times over.
a = 2  # leading coefficient
b = -7; c_0 = 3
# hc: -f .3f
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # larger root
# hc: -b
M_u = 10
M_u = M_u * 2
check = x_1 > 2 and M_u > 1
h = M_u * 3  # hc: -i
'''

# 1-based worksheet rows of SOURCE, in order.
DOC, H2, H3, PARA, A, B, C0, X1, BLANK, MU, MU2, CHECK, H = range(1, 14)


def render(source=SOURCE, **kwargs) -> ExcelWorkbook:
    return HandCalcs(renderer=ExcelRenderer(**kwargs))(source)


def load(workbook: ExcelWorkbook, **kwargs):
    return openpyxl.load_workbook(io.BytesIO(workbook.to_bytes()), **kwargs)


@pytest.fixture(scope="module")
def result():
    return render()


@pytest.fixture(scope="module")
def sheet(result):
    return load(result)["Calculations"]


@pytest.fixture(scope="module")
def values(result):
    return load(result, data_only=True)["Calculations"]


def test_result_object(result, tmp_path):
    assert isinstance(result, ExcelWorkbook)
    assert result.to_bytes()[:2] == b"PK"  # a zip container
    path = result.save(tmp_path / "calc.xlsx")
    assert path.read_bytes() == result.to_bytes()


def test_filepath_option_saves(tmp_path):
    path = tmp_path / "out.xlsx"
    result = render("a = 1\n", filepath=path)
    assert path.read_bytes() == result.to_bytes()


def test_param_row_layout(sheet):
    row = [sheet.cell(A, col).value for col in range(1, 8)]
    assert row == ["a", "=", "leading coefficient", "=", 2, None, None]


def test_calc_row_layout(sheet):
    assert sheet.cell(X1, 1).value is not None
    assert sheet.cell(X1, 2).value == "="
    assert sheet.cell(X1, 4).value == "="
    assert sheet.cell(X1, 5).value == "=(-b+SQRT(b^2-4*a*c_0))/(2*a)"
    assert sheet.cell(X1, 7).value == "larger root"


def test_defined_names_are_sheet_scoped_and_point_at_column_e(sheet, result):
    workbook = load(result)
    assert not workbook.defined_names  # nothing global
    names = {name: dn.attr_text for name, dn in sheet.defined_names.items()}
    assert names == {
        "a": "'Calculations'!$E$%d" % A,
        "b": "'Calculations'!$E$%d" % B,
        "c_0": "'Calculations'!$E$%d" % C0,
        "x_1": "'Calculations'!$E$%d" % X1,
        "M_u": "'Calculations'!$E$%d" % MU,
        "M_u_2": "'Calculations'!$E$%d" % MU2,
        "check": "'Calculations'!$E$%d" % CHECK,
        "h": "'Calculations'!$E$%d" % H,
    }


def test_formulas_reference_the_latest_version(sheet):
    assert sheet.cell(MU2, 5).value == "=M_u*2"
    assert sheet.cell(CHECK, 5).value == "=AND(x_1>2,M_u_2>1)"


def test_cached_values(values):
    assert values.cell(X1, 5).value == pytest.approx(3.0)
    assert values.cell(MU, 5).value == 10
    assert values.cell(MU2, 5).value == 20
    assert values.cell(CHECK, 5).value is True
    assert values.cell(H, 5).value == 60


def test_number_formats(sheet):
    assert sheet.cell(A, 5).number_format == "General"
    assert sheet.cell(X1, 5).number_format == "0.000"


def test_default_value_and_formula_formats(sheet):
    value = sheet.cell(A, 5)
    assert value.fill.fgColor.rgb.endswith("FFF2CC")
    assert not value.font.b
    formula = sheet.cell(X1, 5)
    assert formula.font.b
    assert formula.fill.fill_type is None
    assert value.alignment.horizontal == "right"


def test_custom_value_and_formula_formats():
    result = render(
        "a = 1\nb = a + 1\n",
        value_format={"cell_color": (0, 128, 255), "bold": True},
        formula_format={"text_color": "#FF0000", "cell_color": "DDEEFF"},
    )
    sheet = load(result)["Calculations"]
    assert sheet["E1"].fill.fgColor.rgb.endswith("0080FF")
    assert sheet["E1"].font.b
    assert sheet["E2"].font.color.rgb.endswith("FF0000")
    assert sheet["E2"].fill.fgColor.rgb.endswith("DDEEFF")


def test_headings_merge_a_to_e_with_scaled_sizes(sheet):
    merged = {str(r) for r in sheet.merged_cells.ranges}
    assert {f"A{H2}:E{H2}", f"A{H3}:E{H3}"} <= merged
    assert sheet.cell(H2, 1).value == "Roots"
    assert sheet.cell(H2, 1).font.b
    assert sheet.cell(H2, 1).font.sz == HEADING_SIZES[1] == 16
    assert sheet.cell(H3, 1).font.sz == HEADING_SIZES[2] == 14


def test_comment_paragraph_is_one_merged_wrapped_row(sheet):
    merged = {str(r) for r in sheet.merged_cells.ranges}
    assert f"A{PARA}:E{PARA}" in merged
    cell = sheet.cell(PARA, 1)
    assert cell.value.startswith("Solve a*x**2") and cell.value.endswith("several times over.")
    assert cell.alignment.wrap_text
    # Excel never auto-fits merged rows: the writer sets a multi-line height.
    assert sheet.row_dimensions[PARA].height > 13.2


def test_docstring_is_a_paragraph(sheet):
    assert sheet.cell(DOC, 1).value == "Quadratic roots"


def test_comment_column_is_grey_italic(sheet):
    font = sheet.cell(X1, 7).font
    assert font.i
    assert font.color.rgb.endswith("808080")


def test_body_font_is_10pt(sheet):
    assert sheet.cell(A, 1).font.sz == 10
    assert sheet.cell(X1, 5).font.sz == 10


def test_blank_row(sheet):
    assert all(sheet.cell(BLANK, col).value is None for col in range(1, 8))


def test_ignored_row_is_hidden(sheet):
    assert sheet.row_dimensions[H].hidden
    assert not sheet.row_dimensions[CHECK].hidden


def _runs(rich) -> list:
    """openpyxl rich text as (text, vertAlign); unstyled runs come back as str."""
    return [
        (block, None) if isinstance(block, str) else (block.text, block.font.vertAlign)
        for block in rich
    ]


def test_rich_text_subscripts(result):
    sheet = load(result, rich_text=True)["Calculations"]
    assert _runs(sheet.cell(X1, 1).value) == [("x", None), ("1", "subscript")]
    assert ("2", "superscript") in _runs(sheet.cell(X1, 3).value)


def test_column_widths_are_clamped(sheet):
    widths = {col: sheet.column_dimensions[col].width for col in "ABCDEFG"}
    assert all(w > 0 for w in widths.values())
    assert widths["C"] <= 51  # MIDDLE max 50 (+ openpyxl rounding)


def test_write_sheet_puts_several_cells_in_one_workbook():
    renderer = ExcelRenderer()
    first = HandCalcs(renderer=renderer)("a = 1\nb = a * 2\n").rows
    second = HandCalcs(renderer=renderer)("a = 5\nb = a * 3\n").rows
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    renderer.write_sheet(workbook, first, "Beam 1")
    renderer.write_sheet(workbook, second, "Beam 2")
    workbook.close()
    loaded = openpyxl.load_workbook(io.BytesIO(buffer.getvalue()))
    assert loaded["Beam 1"].defined_names["a"].attr_text == "'Beam 1'!$E$1"
    assert loaded["Beam 2"].defined_names["a"].attr_text == "'Beam 2'!$E$1"
    assert loaded["Beam 2"]["E2"].value == "=a*3"


def test_write_sheet_validates_sheet_name():
    renderer = ExcelRenderer()
    workbook = xlsxwriter.Workbook(io.BytesIO(), {"in_memory": True})
    with pytest.raises(ValueError):
        renderer.write_sheet(workbook, [], "bad/name")
    workbook.close()


def test_demo_renders():
    from handcalcs.renderers.excel.demo import source
    result = render(source, sheet_name="Beam check")
    sheet = load(result)["Beam check"]
    assert sheet.defined_names["M_r_2"].attr_text.startswith("'Beam check'!$E$")
    assert result.rows[-1].cached is True


@pytest.mark.parametrize("source", ["quadratic", "demo"])
def test_recalculated_results_match_python(source, tmp_path):
    """Recalculate with the ``formulas`` package (if installed) and compare."""
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    from handcalcs.renderers.excel.demo import source as demo_source
    result = render(SOURCE if source == "quadratic" else demo_source)
    path = result.save(tmp_path / "calc.xlsx")
    assert recalculation_problems(path, result.rows) == []
