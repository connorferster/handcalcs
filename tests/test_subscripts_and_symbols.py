"""
#101: comma subscripts (the ``subscripts`` option) and
display specs (the ``symbols`` option), parsed once in ``identifiers.py`` and
formatted by every renderer.
"""

import pytest

import handcalcs
from handcalcs import HandCalcs
from handcalcs.renderers.excel.symbolic import symbolic_identifier
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.identifiers import (
    IdentifierOptions,
    SpecError,
    Symbol,
    parse_identifier,
    parse_spec,
)
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.markdown import MarkdownRenderer
from handcalcs.renderers.ascii import ASCIIRenderer

NESTED = IdentifierOptions(subscripts="nested")


def text(*names: str) -> list:
    return [[(False, name)] for name in names]


# --- the parser --------------------------------------------------------------


def test_comma_style_makes_siblings():
    symbol = parse_identifier("N_pl_Rd")
    assert symbol.text() == "N"
    assert [sub.text() for sub in symbol.subscripts] == ["pl", "Rd"]
    assert all(not sub.subscripts for sub in symbol.subscripts)


def test_nested_style_makes_a_chain():
    symbol = parse_identifier("x_a_b", NESTED)
    assert [sub.text() for sub in symbol.subscripts] == ["a"]
    assert [sub.text() for sub in symbol.subscripts[0].subscripts] == ["b"]


@pytest.mark.parametrize(
    "identifier, base, accents, primes, subs, sups",
    [
        ("x_hat", "x", ["hat"], 0, [], []),
        ("x_bar_max", "x", ["bar"], 0, ["max"], []),
        ("M_star", "M", [], 0, [], ["*"]),
        ("f_prime_c", "f", [], 1, ["c"], []),
        ("hat", "hat", [], 0, [], []),
        ("x__y", "x y", [], 0, [], []),
        ("a___b", "a_b", [], 0, [], []),
        ("lambda_", "lamb", [], 0, [], []),
        ("class_", "class", [], 0, [], []),
        ("_private", "_private", [], 0, [], []),
    ],
)
def test_parse_identifier(identifier, base, accents, primes, subs, sups):
    symbol = parse_identifier(identifier)
    assert symbol.text() == base
    assert symbol.accents == accents
    assert symbol.primes == primes
    assert [sub.text() for sub in symbol.subscripts] == subs
    assert [sup.text() for sup in symbol.superscripts] == sups


def test_symbols_option_replaces_the_parse():
    options = IdentifierOptions(symbols={"N_plRd": "N_{pl,Rd}"})
    symbol = parse_identifier("N_plRd", options)
    assert [sub.text() for sub in symbol.subscripts] == ["pl", "Rd"]


@pytest.mark.parametrize(
    "spec, base, subs, sups, primes",
    [
        ("N_{pl,Rd}", "N", ["pl", "Rd"], [], 0),
        ("N_Rd", "N", ["Rd"], [], 0),
        ("M^{*}_{Ed}", "M", ["Ed"], ["*"], 0),
        ("x^2", "x", [], ["2"], 0),
        ("f'_c", "f", ["c"], [], 1),
        ("Delta H", "Delta H", [], [], 0),
        (" N _{ pl , Rd } ", "N", ["pl", "Rd"], [], 0),
    ],
)
def test_parse_spec(spec, base, subs, sups, primes):
    symbol = parse_spec(spec)
    assert symbol.text() == base
    assert [sub.text() for sub in symbol.subscripts] == subs
    assert [sup.text() for sup in symbol.superscripts] == sups
    assert symbol.primes == primes


def test_parse_spec_nesting_and_greek():
    symbol = parse_spec("sigma_{c_{max}}")
    assert symbol.words == [[(True, "sigma")]]
    assert symbol.subscripts[0].subscripts[0].text() == "max"


@pytest.mark.parametrize("spec", ["", "N_", "N_{pl,Rd", "N}", "N_{,}", "^2"])
def test_parse_spec_errors(spec):
    with pytest.raises(SpecError):
        parse_spec(spec)


# --- every renderer ----------------------------------------------------------

# identifier: (plain text, LaTeX and Markdown, HTML, Excel display)
COMMA = {
    "N_pl_Rd": (
        "N_pl_Rd",
        "N_{\\mathrm{pl,Rd}}",
        "N<sub>pl,Rd</sub>",
        "N<sub>pl,Rd</sub>",
    ),
    "f_y_k": ("f_y_k", "f_{y,k}", "f<sub>y,k</sub>", "f<sub>y,k</sub>"),
    "M_Ed_y": ("M_Ed_y", "M_{\\mathrm{Ed},y}", "M<sub>Ed,y</sub>", "M<sub>Ed,y</sub>"),
    "x_hat_max": (
        "x_hat_max",
        "\\hat{x}_{\\mathrm{max}}",
        "x̂<sub>max</sub>",
        "x̂<sub>max</sub>",
    ),
    "M_star": ("M_star", "M^{*}", "M<sup>*</sup>", "M<sup>*</sup>"),
}
NESTED_TABLE = {
    "N_pl_Rd": (
        "N_pl_Rd",
        "N_{\\mathrm{pl}_{\\mathrm{Rd}}}",
        "N<sub>pl<sub>Rd</sub></sub>",
        "N<sub>pl,Rd</sub>",
    ),
}
SYMBOLS = {"N_plRd": "N_{pl,Rd}", "dH": "ΔH^{*}"}
SYMBOL_TABLE = {
    "N_plRd": (
        "N_pl,Rd",
        "N_{\\mathrm{pl,Rd}}",
        "N<sub>pl,Rd</sub>",
        "N<sub>pl,Rd</sub>",
    ),
    "dH": ("ΔH^*", "\\Delta H^{*}", "ΔH<sup>*</sup>", "ΔH<sup>*</sup>"),
}

RENDERERS = [
    (ASCIIRenderer, 0, "{} = 2"),
    (LatexRenderer, 1, "{} &= 2"),
    (MarkdownRenderer, 1, "{} &= 2"),
    (HTMLRenderer, 2, "{} = 2"),
]


def render(renderer, source: str) -> str:
    return HandCalcs(renderer=renderer)(source)


@pytest.mark.parametrize("renderer_class, column, pattern", RENDERERS)
@pytest.mark.parametrize("identifier", COMMA)
def test_comma_style(renderer_class, column, pattern, identifier):
    out = render(renderer_class(), f"{identifier} = 2\n")
    assert pattern.format(COMMA[identifier][column]) in out


@pytest.mark.parametrize("renderer_class, column, pattern", RENDERERS)
@pytest.mark.parametrize("identifier", NESTED_TABLE)
def test_nested_style_comment(renderer_class, column, pattern, identifier):
    source = f'# hc: subscripts = "nested"\n{identifier} = 2\n'
    out = render(renderer_class(), source)
    assert pattern.format(NESTED_TABLE[identifier][column]) in out


@pytest.mark.parametrize("renderer_class, column, pattern", RENDERERS)
@pytest.mark.parametrize("identifier", SYMBOL_TABLE)
def test_symbols_comment(renderer_class, column, pattern, identifier):
    source = f"# hc: symbols = {SYMBOLS!r}\n{identifier} = 2\n"
    out = render(renderer_class(), source)
    assert pattern.format(SYMBOL_TABLE[identifier][column]) in out


@pytest.mark.parametrize("identifier", COMMA)
def test_excel_comma_style(identifier):
    assert symbolic_identifier(identifier) == COMMA[identifier][3]


@pytest.mark.parametrize("identifier", NESTED_TABLE)
def test_excel_is_flat_in_either_style(identifier):
    assert symbolic_identifier(identifier, NESTED) == NESTED_TABLE[identifier][3]


@pytest.mark.parametrize("identifier", SYMBOL_TABLE)
def test_excel_symbols(identifier):
    options = IdentifierOptions(symbols=SYMBOLS)
    assert symbolic_identifier(identifier, options) == SYMBOL_TABLE[identifier][3]


def test_subscripts_section_command():
    out = render(LatexRenderer(), '# hc: subscripts = "nested"\nN_pl_Rd = 2\nf_y_k = 3\n')
    assert "N_{\\mathrm{pl}_{\\mathrm{Rd}}} &= 2" in out
    assert "f_{y_{k}} &= 3" in out


@pytest.mark.parametrize("attribute", ["SUBSCRIPT_STYLE", "GREEK_PREFIXES"])
def test_behaviour_settings_are_not_class_attributes(attribute):
    # Behaviour is set through the render context, the same way for every renderer.
    assert not hasattr(LatexRenderer, attribute)


def test_inline_comment_applies_to_its_line_only():
    source = 'N_pl_Rd = 2  # hc: subscripts = "nested"\nN_b_Rd = 3\n'
    out = render(LatexRenderer(), source)
    assert "N_{\\mathrm{pl}_{\\mathrm{Rd}}} &= 2" in out
    assert "N_{b,\\mathrm{Rd}} &= 3" in out


def test_set_option(monkeypatch, tmp_path):
    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "hc_config.json"))
    handcalcs.reset_config()
    try:
        handcalcs.set_option("subscripts", "nested")
        handcalcs.set_option("symbols", {"V_dot": "V_{dot}"})
        out = render(LatexRenderer(), "N_pl_Rd = 2\nV_dot = 1\n")
    finally:
        handcalcs.reset_config()
    assert "N_{\\mathrm{pl}_{\\mathrm{Rd}}} &= 2" in out
    assert "V_{\\mathrm{dot}} &= 1" in out


# --- accents (dot, ddot, and accent(...) in specs) ---------------------------

ACCENT_SPECS = {"V_flow": "dot(V)", "x_m": "bar(x)_{m}", "s_c": "hat(sigma)'_{c}"}
# identifier or spec key: (LaTeX, HTML, Excel display)
ACCENT_TABLE = {
    "V_dot": ("\\dot{V}", "V̇", "V̇"),
    "x_ddot_1": ("\\ddot{x}_{1}", "ẍ<sub>1</sub>", "ẍ<sub>1</sub>"),
    "V_flow": ("\\dot{V}", "V̇", "V̇"),
    "x_m": ("\\bar{x}_{m}", "x̅<sub>m</sub>", "x̅<sub>m</sub>"),
    "s_c": ("\\hat{\\sigma}'_{c}", "σ̂′<sub>c</sub>", "σ̂′<sub>c</sub>"),
}


@pytest.mark.parametrize("identifier", ACCENT_TABLE)
def test_accents_latex_and_html(identifier):
    source = f"# hc: symbols = {ACCENT_SPECS!r}\n{identifier} = 2\n"
    latex, html, _ = ACCENT_TABLE[identifier]
    assert f"{latex} &= 2" in render(LatexRenderer(), source)
    assert f"{html} = 2" in render(HTMLRenderer(), source)


@pytest.mark.parametrize("identifier", ACCENT_TABLE)
def test_accents_excel(identifier):
    options = IdentifierOptions(symbols=ACCENT_SPECS)
    assert symbolic_identifier(identifier, options) == ACCENT_TABLE[identifier][2]


def test_accent_spec_keeps_subscripts_outside():
    symbol = parse_spec("bar(x_1)")
    assert symbol.accents == ["bar"]
    assert [sub.text() for sub in symbol.subscripts] == ["1"]


@pytest.mark.parametrize("spec", ["tilde(x)", "dot(V", "dot()"])
def test_accent_spec_errors(spec):
    with pytest.raises(SpecError):
        parse_spec(spec)
