"""
#117: every renderer recognises the same Greek letters in an identifier
(``identifiers.py``), so the renderers can't drift apart again.
"""

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers.excel.names import to_excel_name
from handcalcs.renderers.identifiers import IdentifierOptions
from handcalcs.renderers.excel.symbolic import symbolic_identifier
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.markdown import MarkdownRenderer
from handcalcs.renderers.ascii import ASCIIRenderer

# identifier: (plain text, LaTeX and Markdown, HTML, Excel display markup)
TABLE = {
    "DeltaH": ("ΔH", "\\Delta H", "ΔH", "ΔH"),
    "DeltaT_max": (
        "ΔT_max",
        "\\Delta T_{\\mathrm{max}}",
        "ΔT<sub>max</sub>",
        "ΔT<sub>max</sub>",
    ),
    "gammaM0": ("γM0", "\\gamma \\mathrm{M0}", "γM0", "γM0"),
    "alpha2": ("α2", "\\alpha 2", "α2", "α2"),
    "Delta__H": ("Δ H", "\\Delta\\ H", "Δ H", "Δ H"),
    "Delta__E_car": (
        "Δ E_car",
        "\\Delta\\ E_{\\mathrm{car}}",
        "Δ E<sub>car</sub>",
        "Δ E<sub>car</sub>",
    ),
    "ΔH": ("ΔH", "\\Delta H", "ΔH", "ΔH"),
    "Sigma_rho": ("Σ_ρ", "\\Sigma_{\\rho}", "Σ<sub>ρ</sub>", "Σ<sub>ρ</sub>"),
    "metal": ("metal", "\\mathrm{metal}", "metal", "metal"),
    "Annual__Rate": (
        "Annual Rate",
        "\\mathrm{Annual\\ Rate}",
        "Annual Rate",
        "Annual Rate",
    ),
}


def render(renderer, identifier: str) -> str:
    return HandCalcs(renderer=renderer)(f"{identifier} = 2\n")


@pytest.mark.parametrize("identifier", TABLE)
def test_plain_text(identifier):
    assert f"{TABLE[identifier][0]} = 2" in render(ASCIIRenderer(), identifier)


@pytest.mark.parametrize("identifier", TABLE)
def test_latex(identifier):
    assert f"{TABLE[identifier][1]} &= 2" in render(LatexRenderer(), identifier)


@pytest.mark.parametrize("identifier", TABLE)
def test_markdown(identifier):
    assert f"{TABLE[identifier][1]} &= 2" in render(MarkdownRenderer(), identifier)


@pytest.mark.parametrize("identifier", TABLE)
def test_html(identifier):
    assert f"{TABLE[identifier][2]} = 2" in render(HTMLRenderer(), identifier)


@pytest.mark.parametrize("identifier", TABLE)
def test_excel_display(identifier):
    assert symbolic_identifier(identifier) == TABLE[identifier][3]


@pytest.mark.parametrize(
    "renderer_class, expected",
    [
        (ASCIIRenderer, "DeltaH = 2"),
        (LatexRenderer, "\\mathrm{DeltaH} &= 2"),
        (MarkdownRenderer, "\\mathrm{DeltaH} &= 2"),
        (HTMLRenderer, "DeltaH = 2"),
    ],
)
def test_greek_prefixes_off(renderer_class, expected):
    class NoPrefixes(renderer_class):
        GREEK_PREFIXES = False

    assert expected in render(NoPrefixes(), "DeltaH")


NO_PREFIXES = IdentifierOptions(greek_prefixes=False)


def test_excel_display_with_greek_prefixes_off():
    assert symbolic_identifier("DeltaH", NO_PREFIXES) == "DeltaH"
    assert symbolic_identifier("Delta__H", NO_PREFIXES) == "Δ H"


@pytest.mark.parametrize("identifier", ["DeltaH", "gammaM0", "Delta__H", "sigma_max"])
def test_excel_defined_names_keep_the_raw_identifier(identifier):
    # Only the display column changes; the defined name comes from the source.
    assert to_excel_name(identifier) == identifier
