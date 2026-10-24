"""
Tests for the ExcelRenderer configuration: cell-format dicts, colour
normalization, sheet-name rules and the renderer registry entry.
"""
import pytest

from handcalcs.renderers import get_renderer
from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError
from handcalcs.renderers.excel.options import normalize_color


def test_registered_as_excel():
    assert get_renderer('excel') is ExcelRenderer


def test_defaults():
    r = ExcelRenderer()
    assert r.sheet_name == "Calculations"
    assert r.value_format == {"bold": False, "text_color": "#000000", "cell_color": "#FFF2CC"}
    assert r.formula_format == {"bold": True, "text_color": "#000000", "cell_color": None}
    assert r.filepath is None
    assert r.general_format == "General"


def test_user_format_merges_over_defaults():
    r = ExcelRenderer(value_format={"bold": True}, formula_format={"cell_color": "ddebf7"})
    assert r.value_format == {"bold": True, "text_color": "#000000", "cell_color": "#FFF2CC"}
    assert r.formula_format["cell_color"] == "#DDEBF7"
    assert r.formula_format["bold"] is True


def test_user_format_does_not_mutate_defaults():
    ExcelRenderer(value_format={"bold": True})
    assert ExcelRenderer().value_format["bold"] is False


@pytest.mark.parametrize("value, expected", [
    ("#ff0000", "#FF0000"),
    ("00ff00", "#00FF00"),
    (" #0000Ff ", "#0000FF"),
    ((255, 128, 0), "#FF8000"),
    ([0, 0, 0], "#000000"),
    (None, None),
])
def test_normalize_color(value, expected):
    assert normalize_color(value, "opt") == expected


@pytest.mark.parametrize("value", [
    "#fff", "red", "#GG0000", (256, 0, 0), (1, 2), (1.0, 2, 3), (True, 0, 0), 0xFF0000,
])
def test_invalid_color_raises(value):
    with pytest.raises(ValueError, match="text_color"):
        ExcelRenderer(formula_format={"text_color": value})


def test_unknown_format_key_raises():
    with pytest.raises(ValueError, match="unknown key"):
        ExcelRenderer(value_format={"italic": True})


def test_format_must_be_dict():
    with pytest.raises(ValueError, match="must be a dict"):
        ExcelRenderer(value_format=["bold"])


def test_bold_must_be_bool():
    with pytest.raises(ValueError, match="bold"):
        ExcelRenderer(value_format={"bold": 1})


@pytest.mark.parametrize("name", ["", "a" * 32, "a/b", "x[1]", "'quoted'", "History", 5])
def test_invalid_sheet_name_raises(name):
    with pytest.raises(ValueError):
        ExcelRenderer(sheet_name=name)


def test_valid_sheet_name():
    assert ExcelRenderer(sheet_name="Beam B-1 (L=6 m)").sheet_name == "Beam B-1 (L=6 m)"


def test_filepath_is_a_path(tmp_path):
    r = ExcelRenderer(filepath=str(tmp_path / "calc.xlsx"))
    assert r.filepath == tmp_path / "calc.xlsx"


def test_error_message_names_target():
    err = ExcelRendererIncompatibleError("lists are not supported").with_target("x")
    assert str(err) == "Cannot render to Excel: lists are not supported (in the assignment to 'x')"
    assert err.reason == "lists are not supported"
