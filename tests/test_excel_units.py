"""
Tests for values with units (pint, forallpeople): display magnitudes and unit
text in the cells, formulas with unit factors only where they are needed, and
skipped units setup lines.
"""
import builtins
from fractions import Fraction

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
    assert (info.magnitude, info.unit, info.factor) == (300, "mm", Fraction(1, 1000))
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


def test_formulas_fold_unit_factors(structural):
    r = run_fap()
    m = r["M"]
    assert isinstance(m, CalcRow)
    # kN·mm and kN/m·mm² differ by 1000: the second term is brought to the first.
    assert m.formula == "=(F*L+w*L^2/8/1000)/1000"
    assert m.unit == "kN·m"
    assert m.cached == pytest.approx(3.7725)
    assert r["sigma"].formula == "=M/(L^3/6)*1000000000"
    assert r["sigma"].unit == "kPa"
    assert r["sigma"].cached == pytest.approx(838.3333333)


def test_dimensionless_result_has_no_unit(structural):
    ratio = run_fap()["ratio"]
    assert ratio.unit is None
    assert ratio.formula == "=M/(F*L)*1000"
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
    # A bare unit is a factor: 12 * mm is 12 in a row of millimetres.
    assert r["t"].formula == "=IF(L>250,12,8)"
    assert (r["t"].cached, r["t"].unit) == (12, "mm")
    assert r["A"].formula == "=L*t"
    assert (r["A"].cached, r["A"].unit) == (3600, "mm²")


def test_attribute_units_without_top_level(structural):
    r = rows("import forallpeople as si\nL = 300 * si.mm\nA = L * 2\n")
    assert (r["L"].value, r["L"].unit) == (300, "mm")
    assert r["A"].formula == "=L*2"


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
    assert r["M"].formula == "=F*L"  # kN·mm is N·m
    # pint 0.26 joins units with "⋅" (U+22C5); pint 0.25 (the newest on Python
    # 3.11) uses "·" (U+00B7). The renderer passes pint's text through.
    assert (r["M"].cached, r["M"].unit.replace("·", "⋅")) == (3750, "kN⋅mm")
    assert r["A"].formula == "=L^2"
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


# --- unit conversions: .to() ---

TO = """import forallpeople as si
F = 2 * si.kN
L = 3 * si.ft
phi = 0.9
M = (F * L).to('kipft')
M = M.to('kipin')
M_r = phi * (F * L).to('kipft')
"""


def test_to_sets_the_display_unit(structural):
    r = rows(TO)
    # The conversion adds no Excel: the row's own unit sets the factor left.
    # kN·ft to kip·ft is the number of N in a lbf.
    assert r["M"].formula == "=F*L/4.4482216152605"
    assert (r["M"].cached, r["M"].unit) == (pytest.approx(1.348853659), "kip·ft")
    assert r["M_r"].formula == "=phi*(F*L)/4.4482216152605"
    assert r["M_r"].unit == "kip·ft"


def test_reassigned_to_converts_the_previous_version(structural):
    m2 = rows(TO)["M_2"]
    assert m2.formula == "=M*12"
    assert (m2.cached, m2.unit) == (pytest.approx(16.18624390), "kip·in")


def test_to_shows_only_the_converted_value(structural):
    from handcalcs.renderers.excel.rich_text import plain_text
    r = rows(TO)
    assert plain_text(r["M"].symbolic) == "(F · L)"
    assert plain_text(r["M_2"].symbolic) == "M"
    assert plain_text(r["M_r"].symbolic) == "φ · (F · L)"


def test_pint_to_with_strings_and_unit_expressions():
    source = PINT + "M_kNm = M.to('kN*m')\nM_kipft = M.to(ureg.kip * ureg.ft)\n"
    r = rows(source)
    assert r["M_kNm"].formula == "=M/1000"
    assert r["M_kNm"].cached == pytest.approx(3.75)
    assert r["M_kipft"].formula == "=M/1355.8179483314"  # pint's float factor
    assert r["M_kipft"].cached == pytest.approx(2.765858060)


def test_to_on_a_plain_number_still_raises():
    with pytest.raises(ExcelRendererIncompatibleError, match=r"'a\.to\(\)'"):
        HandCalcs(renderer=ExcelRenderer())(
            "a = 2\nb = a.to('kip')\n", supplied_globals={"a": 2, "b": 2}
        )


def test_to_recalculates_like_python(structural, tmp_path):
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    result = HandCalcs(renderer=ExcelRenderer())(TO)
    path = result.save(tmp_path / "to.xlsx")
    assert recalculation_problems(path, result.rows) == []


# --- round(), float() and int() of values with units ---

CASTS = """import forallpeople as si
si.environment('structural')
from math import sqrt
f_c = 4 * si.ksi
M = 10.0 * si.kN * si.m
P = 2083.0 * si.kN
F = -4.7 * si.kN
a = 2.675
e = round(M / P, 3)
v_c = 4 * sqrt(float(f_c / si.psi)) * si.psi
f_num = float(f_c)
g = 2 * float(M) + 1
n = int(F)
r_a = round(a * 3, 1)
i = int(-a * 3)
h = float(a + 1) * 2
"""


@pytest.fixture
def structural_env():
    yield
    si.environment("default", top_level=False)


def cast_rows():
    return rows(CASTS)


def test_round_of_a_physical_keeps_the_value(structural_env):
    # forallpeople's round() only sets the digits shown: 4.80 mm, not ROUND in metres (5 mm).
    e = cast_rows()["e"]
    assert e.formula == "=M/P"  # kN·m / MN is mm
    assert (e.cached, e.unit) == (pytest.approx(4.800768123), "mm")


def test_float_and_int_of_a_physical_use_its_display_magnitude(structural_env):
    r = cast_rows()
    assert r["v_c"].cached == pytest.approx(252.9822128)  # sqrt(4000 psi), ACI style
    assert r["v_c"].formula == "=4*SQRT(f_c*1000)"  # f_c / psi, f_c in ksi
    assert r["f_num"].formula == "=f_c"
    assert r["f_num"].cached == 4.0 and r["f_num"].unit is None
    assert r["g"].formula == "=2*M+1"
    assert r["n"].formula == "=TRUNC(F)"
    assert r["n"].cached == -4  # toward zero, like Python


def test_round_float_int_of_plain_numbers(structural_env):
    r = cast_rows()
    assert r["r_a"].formula == "=ROUND(a*3,1)"
    assert r["i"].formula == "=TRUNC(-a*3)"
    assert r["h"].formula == "=(a+1)*2"  # float() adds nothing


def test_pint_round_float_int():
    source = PINT + (
        "r = round(L * 1.23456, 1)\n"
        "d = float(L / (7 * ureg.m))\n"
        "n = int(L / (7 * mm))\n"
    )
    r = rows(source)
    # pint rounds the magnitude in the quantity's own unit (mm).
    assert r["r_"].formula == "=ROUND(L*1.23456,1)"
    assert (r["r_"].cached, r["r_"].unit) == (pytest.approx(370.4), "mm")
    assert r["d"].cached == pytest.approx(300 / 7000)
    assert r["d"].formula == "=L/7/1000"
    assert r["n"].formula == "=TRUNC(L/7)"
    assert r["n"].cached == 42


def test_casts_recalculate_like_python(structural_env, tmp_path):
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    for source in (CASTS, PINT + "r = round(L * 1.23456, 1)\nn = int(L / (7 * mm))\n"):
        result = HandCalcs(renderer=ExcelRenderer())(source)
        path = result.save(tmp_path / "casts.xlsx")
        assert recalculation_problems(path, result.rows) == []


# --- unit factors only where needed (US units) ---

from handcalcs.renderers.excel.formulas import factor_text

US = """import forallpeople as si
si.environment('us_structural')
L = 24 * si.ft
w_D = 0.45 * si.kip / si.ft
w_L = 0.80 * si.kip / si.ft
w_u = 1.2 * w_D + 1.6 * w_L
M_u = w_u * L**2 / 8
F_y = 50 * si.ksi
Z_x = 54.6 * si.inch**3
phi = 0.9
phi_M_n = phi * F_y * Z_x
DCR = M_u / phi_M_n
ok = M_u <= phi_M_n
M_2 = M_u + phi_M_n
M_max = max(M_u, phi_M_n)
A_s = 2.37 * si.inch**2
b = 12 * si.inch
d = 21.5 * si.inch
f_c = 4000 * si.psi
a = A_s * F_y / (0.85 * f_c * b)
M_rc = A_s * F_y * (d - a / 2)
s = 12 * si.inch if a > 2 * si.inch else 18 * si.inch
pos = M_u > 0
n = 2
I_n = b * d**n
"""


@pytest.fixture
def us_rows():
    yield rows(US)
    si.environment("default", top_level=False)


@pytest.mark.parametrize(
    "ratio, expected",
    [
        (1, None),
        (Fraction(1, 12), ("/", "12")),
        (12, ("*", "12")),
        (Fraction(1, 8), ("/", "8")),  # not *0.125
        (1000, ("*", "1000")),
        (Fraction(1, 1000), ("/", "1000")),
        (Fraction("25.4"), ("*", "25.4")),
        (1 / Fraction("25.4"), ("/", "25.4")),
        (Fraction("2.5"), ("*", "2.5")),
        (Fraction(1) / Fraction("4.4482216152605"), ("/", "4.4482216152605")),
        (0.30479999999999996, ("*", "0.3048")),  # float noise
        (0.9999999999999998, None),
    ],
)
def test_factor_text(ratio, expected):
    assert factor_text(ratio) == expected


def test_factors_that_cancel_are_not_written(us_rows):
    r = us_rows
    assert r["w_u"].formula == "=1.2*w_D+1.6*w_L"
    assert r["M_u"].formula == "=w_u*L^2/8"
    assert r["phi_M_n"].formula == "=phi*F_y*Z_x"
    assert r["M_rc"].formula == "=A_s*F_y*(d-a/2)"


def test_factors_that_remain_are_simple(us_rows):
    r = us_rows
    # kip·ft against kip·in
    assert r["DCR"].formula == "=M_u/phi_M_n*12"
    assert r["ok"].formula == "=M_u<=phi_M_n/12"
    # A sum is brought to the unit of its row (kip·ft, the unit of M_u).
    assert r["M_2"].formula == "=M_u+phi_M_n/12"
    assert r["M_max"].formula == "=MAX(M_u*12,phi_M_n)"
    # ksi / psi, in inches (the environment's default length)
    assert r["a"].formula == "=A_s*F_y/(0.85*f_c*b)*1000"
    assert r["a"].unit == "in"


def test_bare_units_and_zero_need_no_factor(us_rows):
    assert us_rows["s"].formula == "=IF(a>2,12,18)"
    assert us_rows["pos"].formula == "=M_u>0"


def test_a_power_of_a_row_is_in_si(us_rows):
    # The power of the factor is unknown until the sheet runs.
    assert us_rows["I_n"].formula == "=b*(d*0.0254)^n/0.00064516"


@pytest.mark.parametrize("environment", ["us_structural", "structural"])
def test_folded_formulas_recalculate_like_python(environment, tmp_path):
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    conditional = (
        "import forallpeople as si\n"
        f"si.environment('{environment}')\n"
        "L = 20 * si.ft\nd = 18 * si.inch\nM = 50 * si.kip * si.ft\n"
        "if L > 15 * si.ft:\n    t = 2 * si.inch\n    M_x = M * 1.5\n"
        "elif d < 10 * si.inch:\n    t = 1.5 * si.inch\n    M_x = M\n"
        "else:\n    t = L / 100\n    M_x = M + 10 * si.kip * si.inch\n"
        "y = t * 2 + d\n"
    )
    pint_us = (
        "import pint\nureg = pint.UnitRegistry()\n"
        "L = 24 * ureg.ft\nw = 1.82 * ureg.kip / ureg.ft\n"
        "M = (w * L**2 / 8).to('kip * ft')\n"
        "M_n = (50 * ureg.ksi * 54.6 * ureg.inch**3).to('kip * inch')\n"
        "DCR = M / M_n\nM_2 = (M + M_n).to('kip * ft')\nbig = max(M, M_n)\n"
    )
    try:
        for source in (US.replace("us_structural", environment), conditional, pint_us):
            result = HandCalcs(renderer=ExcelRenderer())(source)
            path = result.save(tmp_path / "folded.xlsx")
            assert recalculation_problems(path, result.rows) == []
    finally:
        si.environment("default", top_level=False)
