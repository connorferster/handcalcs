"""
Tests for values with units (pint, forallpeople): display magnitudes and unit
text in the cells, SI-scaled formulas, and skipped units setup lines.
"""
import builtins

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError
from handcalcs.renderers.excel.rows import CalcRow, ParamRow
from handcalcs.renderers.excel.units import is_units_setup, unit_constant, unit_value

si = pytest.importorskip("forallpeople")
pint = pytest.importorskip("pint")

UREG = pint.UnitRegistry()


@pytest.fixture
def structural(monkeypatch):
    """forallpeople's structural environment, with top_level names simulated in builtins."""
    si.environment("structural", top_level=False)
    for unit in ("mm", "m", "kN", "MPa", "kPa"):
        monkeypatch.setattr(builtins, unit, getattr(si, unit), raising=False)
    yield si
    si.environment("default", top_level=False)


def rows(source: str) -> dict:
    result = HandCalcs(renderer=ExcelRenderer())(source)
    return {row.name: row for row in result.rows if hasattr(row, "name")}


# --- units.py ---

def test_pint_unit_value():
    info = unit_value(300 * UREG.mm)
    assert (info.magnitude, info.unit, info.factor) == (300, "mm", 0.001)
    assert unit_value(12 * UREG.kN).factor == 1000
    assert unit_value(4.5 * UREG.MPa).factor == 1e6
    assert unit_value(2.0) is None


def test_pint_offset_units_raise():
    with pytest.raises(ExcelRendererIncompatibleError, match="offset unit"):
        unit_value(UREG.Quantity(20, UREG.degC))


def test_physical_unit_value(structural):
    info = unit_value(300 * si.mm)
    assert (info.magnitude, info.unit, info.factor) == (300, "mm", 0.001)
    info = unit_value(12.5 * si.kN * (300 * si.mm))
    assert (info.magnitude, info.unit, info.factor) == (3.75, "kN·m", 1000)


def test_unit_constants(structural):
    assert unit_constant(UREG.mm) == 0.001
    assert unit_constant(si.mm) == 0.001
    assert unit_constant(si.kN) == 1000
    assert unit_constant(300 * si.mm) is None  # a value, not a unit
    assert unit_constant(2.0) is None


def test_units_setup_detection(structural):
    assert is_units_setup(UREG)
    assert is_units_setup(UREG.mm)
    assert is_units_setup(si)
    assert is_units_setup(si.environment)
    assert not is_units_setup(300 * si.mm)
    assert not is_units_setup(300 * UREG.mm)
    assert not is_units_setup(3.0)


# --- rows (forallpeople) ---

FAP = """import forallpeople as si
si.environment('structural', top_level=True)
F = 12.5 * kN  # point load
L = 300 * mm
w = 2 * kN / m
M = F * L + w * L**2 / 8
sigma = M / (L**3 / 6)
ratio = M / (F * L)
"""


def run_fap(source=FAP):
    # The cell's own si.environment(top_level=True) would write to builtins for
    # the whole session; the fixture's monkeypatched names stand in for it.
    return rows(source.replace("top_level=True", "top_level=False"))


def test_unit_inputs_are_params(structural):
    r = run_fap()
    assert isinstance(r["F"], ParamRow)
    assert (r["F"].value, r["F"].unit, r["F"].formula) == (12.5, "kN", None)
    assert (r["L"].value, r["L"].unit) == (300, "mm")
    assert (r["w"].value, r["w"].unit) == (2, "kN/m")
    assert r["F"].comment == "point load"


def test_formulas_scale_references_to_si_and_back(structural):
    r = run_fap()
    m = r["M"]
    assert isinstance(m, CalcRow)
    assert m.formula == "=(F*1000*(L*0.001)+w*1000*(L*0.001)^2/8)/1000"
    assert m.unit == "kN·m"
    assert m.cached == pytest.approx(3.7725)
    assert r["sigma"].formula == "=M*1000/((L*0.001)^3/6)/1000"
    assert r["sigma"].unit == "kPa"
    assert r["sigma"].cached == pytest.approx(838.3333333)


def test_dimensionless_result_has_no_unit(structural):
    ratio = run_fap()["ratio"]
    assert ratio.unit is None
    assert ratio.formula == "=M*1000/(F*1000*(L*0.001))"
    assert ratio.cached == pytest.approx(1.006)


def test_si_units_need_no_factors(structural):
    r = run_fap("import forallpeople as si\nL = 3 * m\nA = L * L\n")
    assert r["A"].formula == "=L*L"
    assert r["A"].unit == "m²"


def test_units_in_a_conditional(structural):
    source = (
        "import forallpeople as si\nL = 300 * mm\n"
        "if L > 250 * mm:\n    t = 12 * mm\nelse:\n    t = 8 * mm\n"
        "A = L * t\n"
    )
    r = run_fap(source)
    assert r["t"].formula == "=IF(L*0.001>250*0.001,12*0.001,8*0.001)/0.001"
    assert (r["t"].cached, r["t"].unit) == (12, "mm")
    assert r["A"].formula == "=L*0.001*(t*0.001)/1E-06"
    assert (r["A"].cached, r["A"].unit) == (3600, "mm²")


def test_attribute_units_without_top_level(structural):
    r = rows("import forallpeople as si\nL = 300 * si.mm\nA = L * 2\n")
    assert (r["L"].value, r["L"].unit) == (300, "mm")
    assert r["A"].formula == "=L*0.001*2/0.001"


# --- rows (pint) ---

PINT = """import pint
ureg = pint.UnitRegistry()
mm = ureg.mm
F = 12.5 * ureg.kN
L = 300 * mm
M = F * L
A = L**2
"""


def test_pint_setup_lines_are_skipped():
    r = rows(PINT)
    assert set(r) == {"F", "L", "M", "A"}


def test_pint_rows():
    r = rows(PINT)
    assert (r["F"].value, r["F"].unit) == (12.5, "kN")
    assert r["M"].formula == "=F*1000*(L*0.001)"  # kN·mm is SI-equivalent (N·m)
    assert (r["M"].cached, r["M"].unit) == (3750, "kN⋅mm")
    assert r["A"].formula == "=(L*0.001)^2/1E-06"
    assert (r["A"].cached, r["A"].unit) == (90000, "mm²")


def test_other_imports_still_raise():
    with pytest.raises(ExcelRendererIncompatibleError, match="numpy"):
        # supplied_globals: the cell is parsed but not executed (no numpy needed)
        HandCalcs(renderer=ExcelRenderer())("import numpy as np\na = 1\n", supplied_globals={"a": 1})


def test_recalculation_matches_python(structural, tmp_path):
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    for source in (FAP.replace("top_level=True", "top_level=False"), PINT):
        result = HandCalcs(renderer=ExcelRenderer())(source)
        path = result.save(tmp_path / "units.xlsx")
        assert recalculation_problems(path, result.rows) == []
