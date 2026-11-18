"""
forallpeople 4 shows a defined unit as its unit alone (``kN``, not ``1 kN``).
handcalcs works with both: no brackets around a bare unit raised to a power,
no repeated step, and the Excel renderer reads ``display()`` rather than text.
"""

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer
from handcalcs.units import displays_bare

si = pytest.importorskip("forallpeople")


@pytest.fixture
def units() -> dict:
    si.environment("structural")
    return {"mm": si.mm, "kN": si.kN, "m": si.m}


def bare() -> bool:
    si.environment("structural")
    return repr(si.kN) == "kN"


needs_bare_units = pytest.mark.skipif(
    not bare(), reason="this forallpeople shows units with a number"
)


def render(renderer, source: str, namespace: dict) -> str:
    exec(source, namespace)
    return HandCalcs(renderer).render_run(source, namespace)


class Shown:
    """A stand-in Physical that says whether it shows as its unit alone."""

    dimensions = value = None

    def __init__(self, bare: bool):
        self.bare = bare

    def shows_bare_unit(self):
        return self.bare


Shown.__name__ = "Physical"


def test_displays_bare():
    assert displays_bare(Shown(True))
    assert not displays_bare(Shown(False))
    assert not displays_bare(5)


def test_html_columns_compare_without_var():
    assert HTMLRenderer().same_column("<var>kN</var>", "kN")
    assert not HTMLRenderer().same_column("<var>a</var>", "2")


@needs_bare_units
def test_a_bare_unit_power_is_not_bracketed(units):
    out = render(ASCIIRenderer(), "A = 300 * mm**2\n", units)
    assert out == "A = 300 * mm² = 300 mm²\n"
    latex = render(LatexRenderer(), "A = 300 * mm**2\n", units)
    assert "\\left(\\mathrm{mm}\\right)" not in latex


@needs_bare_units
def test_a_quantity_power_is_still_bracketed(units):
    units["L"] = 6 * si.m
    out = render(ASCIIRenderer(), "A = L**2\n", units)
    assert "(6 m)²" in out


@needs_bare_units
def test_html_drops_a_repeated_step(units):
    out = render(HTMLRenderer(), "d = kN\nw = 5 * kN / m\n", units)
    body = out.split("</style>")[1]
    assert '<var>d</var> = <span class="hc-result">' not in body
    assert body.replace("<var>", "").replace("</var>", "").count("5 · kN") == 1


@needs_bare_units
def test_excel_reads_display(units, tmp_path):
    pytest.importorskip("openpyxl")
    from openpyxl import load_workbook

    from handcalcs.renderers.excel import ExcelRenderer

    source = (
        "import forallpeople as si\nsi.environment('structural')\n"
        "b = 300 * si.mm\nA = b * 2 * si.mm\n"
    )
    path = tmp_path / "units.xlsx"
    HandCalcs(ExcelRenderer())(source, destination=path)
    rows = [
        row
        for row in load_workbook(path).active.iter_rows(values_only=True)
        if any(cell is not None for cell in row)
    ]
    assert ("b", "=", None, "=", 300, "mm") in rows
    assert rows[-1][-1] == "mm²"


@needs_bare_units
def test_word_drops_a_repeated_step(units):
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer
    from handcalcs.testing import output_text

    exec("d = kN\n", units)
    text = output_text(HandCalcs(WordRenderer()).render_run("d = kN\n", units))
    assert text.count("kN") == 1
