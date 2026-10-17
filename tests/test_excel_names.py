"""
Tests for Excel defined-name mangling, the SymbolTable and number formats.
"""
import pytest

from handcalcs.renderers.excel import ExcelRendererIncompatibleError
from handcalcs.renderers.excel.names import (
    SymbolTable,
    is_valid_excel_name,
    quote_sheet_name,
    scoped_name,
    to_excel_name,
)
from handcalcs.renderers.excel.number_formats import to_excel_number_format


# --- name validity and mangling ---

@pytest.mark.parametrize("identifier", [
    "x", "M_u", "phi", "alpha_1", "_private", "ABCD1", "x_1", "Fy", "theta_b", "λ",
])
def test_valid_identifiers_pass_through(identifier):
    assert to_excel_name(identifier) == identifier


@pytest.mark.parametrize("identifier, expected", [
    ("x1", "x1_"),
    ("L1", "L1_"),
    ("AB12", "AB12_"),
    ("XFD1048576", "XFD1048576_"),
    ("R1C1", "R1C1_"),
    ("RC", "RC_"),
    ("R2C", "R2C_"),
    ("c", "c_"),
    ("r", "r_"),
    ("C", "C_"),
    ("R", "R_"),
    ("R1", "R1_"),
    ("TRUE", "TRUE_"),
    ("false", "false_"),
])
def test_reference_like_identifiers_get_trailing_underscore(identifier, expected):
    assert to_excel_name(identifier) == expected
    assert is_valid_excel_name(expected)


@pytest.mark.parametrize("name", ["x1", "c", "R1C1", "1x", "", "a b", "TRUE", "a" * 256])
def test_invalid_excel_names(name):
    assert not is_valid_excel_name(name)


def test_non_identifier_raises():
    with pytest.raises(ExcelRendererIncompatibleError):
        to_excel_name("a-b")


# --- SymbolTable ---

def test_assign_and_lookup():
    table = SymbolTable()
    assert table.assign("x1") == "x1_"
    assert table.lookup("x1") == "x1_"
    assert "x1" in table


def test_reassignment_is_versioned():
    table = SymbolTable()
    assert table.assign("M_u") == "M_u"
    assert table.assign("M_u") == "M_u_2"
    assert table.lookup("M_u") == "M_u_2"
    assert table.assign("M_u") == "M_u_3"


def test_version_collides_with_user_name():
    table = SymbolTable()
    table.assign("a_2")
    table.assign("a")
    # a's second version would be "a_2", which the user already took.
    assert table.assign("a") == "a_2_2"
    assert table.lookup("a_2") == "a_2"


def test_collisions_are_case_insensitive():
    table = SymbolTable()
    assert table.assign("Fy") == "Fy"
    assert table.assign("FY") == "FY_2"


def test_mangled_name_collides_with_user_name():
    table = SymbolTable()
    assert table.assign("x1_") == "x1_"
    assert table.assign("x1") == "x1__2"


def test_lookup_unknown_raises_naming_the_variable():
    table = SymbolTable()
    with pytest.raises(ExcelRendererIncompatibleError, match="'b' is used before it is assigned"):
        table.lookup("b")
    assert table.get("b") is None


def test_names_is_a_copy():
    table = SymbolTable()
    table.assign("a")
    table.names["a"] = "zzz"
    assert table.lookup("a") == "a"


def test_scoped_names():
    assert quote_sheet_name("Calc's") == "'Calc''s'"
    assert scoped_name("Calculations", "x") == "'Calculations'!x"


# --- number formats ---

@pytest.mark.parametrize("code, expected", [
    (".3f", "0.000"),
    (".0f", "0"),
    ("f", "0.000000"),
    (",.2f", "#,##0.00"),
    ("_.2f", "#,##0.00"),
    (">10.2f", "0.00"),
    (".2e", "0.00E+00"),
    (".0E", "0E+00"),
    (".1%", "0.0%"),
    (".0%", "0%"),
    ("d", "0"),
    (",d", "#,##0"),
    ("+.2f", "+0.00;-0.00;0.00"),
])
def test_number_formats(code, expected):
    assert to_excel_number_format(code) == expected


@pytest.mark.parametrize("code", [".5g", "g", ".3G", "", "n"])
def test_general_codes_use_general_format(code):
    assert to_excel_number_format(code) == "General"
    assert to_excel_number_format(code, general_format="0.000") == "0.000"


@pytest.mark.parametrize("code", ["s", "x", "~P", ".2fz!", "nonsense"])
def test_unmappable_codes_warn_and_fall_back(code):
    with pytest.warns(UserWarning):
        assert to_excel_number_format(code) == "General"
