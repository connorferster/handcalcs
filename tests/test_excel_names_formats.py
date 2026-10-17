"""
Tests for the ExcelRenderer's pure helpers: Excel defined-name validation,
mangling and versioning (``names.py``), and the Python format spec -> Excel
number format mapping (``number_formats.py``).
"""
import pytest

from handcalcs.renderers.excel import ExcelRendererIncompatibleError
from handcalcs.renderers.excel.names import SymbolTable, excel_safe_name, is_valid_excel_name
from handcalcs.renderers.excel.number_formats import to_excel_format


@pytest.mark.parametrize("name", [
    "M_u", "x_1", "omega_2", "class_section", "F_y", "_private", "σ", "a.b", "xfd", "LONGNAME1",
])
def test_valid_names(name):
    assert is_valid_excel_name(name)


@pytest.mark.parametrize("name", [
    "x1", "L1", "AB12", "XFD1048576", "c", "r", "C", "R", "R1C1", "rc", "R1", "C12", "RC1",
    "TRUE", "false", "", "1a", "a-b", "a" * 256,
])
def test_invalid_names(name):
    assert not is_valid_excel_name(name)


@pytest.mark.parametrize("identifier, expected", [
    ("M_u", "M_u"), ("x1", "x1_"), ("c", "c_"), ("R1C1", "R1C1_"), ("TRUE", "TRUE_"),
])
def test_excel_safe_name(identifier, expected):
    assert excel_safe_name(identifier) == expected


def test_symbol_table_assign_and_lookup():
    st = SymbolTable()
    assert st.assign("a") == "a"
    assert st.assign("x1") == "x1_"
    assert st.lookup("a") == "a"
    assert st.lookup("x1") == "x1_"
    assert st.lookup("missing") is None
    assert "a" in st and "missing" not in st


def test_symbol_table_versions_reassignment():
    st = SymbolTable()
    assert st.assign("M_u") == "M_u"
    assert st.lookup("M_u") == "M_u"
    assert st.assign("M_u") == "M_u_2"
    assert st.lookup("M_u") == "M_u_2"
    assert st.assign("M_u") == "M_u_3"


def test_symbol_table_is_case_insensitive():
    st = SymbolTable()
    assert st.assign("L") == "L"
    assert st.assign("l") == "l_"
    assert st.lookup("L") == "L"


def test_symbol_table_avoids_collision_with_mangled_name():
    st = SymbolTable()
    assert st.assign("x1") == "x1_"
    assert st.assign("x1_") == "x1__"


def test_symbol_table_version_does_not_collide_with_user_name():
    st = SymbolTable()
    st.assign("M_u_2")
    st.assign("M_u")
    assert st.assign("M_u") == "M_u_2_"


def test_require_unknown_raises():
    st = SymbolTable()
    with pytest.raises(ExcelRendererIncompatibleError, match="'q' is used but never assigned"):
        st.require("q")


@pytest.mark.parametrize("code, expected", [
    (".3f", "0.000"),
    (".0f", "0"),
    ("f", "0.000000"),
    (",.2f", "#,##0.00"),
    ("_.1f", "#,##0.0"),
    (".2e", "0.00E+00"),
    (".3E", "0.000E+00"),
    (".1%", "0.0%"),
    (".0%", "0%"),
    ("d", "0"),
    (",d", "#,##0"),
    ("+.2f", "+0.00;-0.00;0.00"),
    ("10.2f", "0.00"),
    (">10.2f", "0.00"),
    (".5g", "General"),
    ("g", "General"),
    (".3", "General"),
    ("", "General"),
    (None, "General"),
])
def test_to_excel_format(code, expected):
    assert to_excel_format(code) == expected


def test_general_format_is_configurable():
    assert to_excel_format(".5g", general_format="0.000") == "0.000"


@pytest.mark.parametrize("code", ["x", "s", "not a spec"])
def test_unmappable_format_warns(code):
    with pytest.warns(UserWarning):
        assert to_excel_format(code) == "General"
