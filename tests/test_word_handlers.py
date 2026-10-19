"""
Tests for the Word renderer's inline handlers (#222), run through the HandCalcs
pipeline. Each rendered OMML fragment is parsed and read back as linear text
(see ``linear``) so the assertions stay readable.
"""

import pytest

pytest.importorskip("lxml")

from handcalcs import HandCalcs
from handcalcs.renderers.base import BaseRenderer
from handcalcs.renderers.identifiers import IdentifierOptions
from handcalcs.renderers.word import WordRenderer, omml
from handcalcs.renderers.word.document import CalcGrid, ParamsTable
from handcalcs.renderers.word.handlers import typeset_number, word_identifier

M = f"{{{omml.M_NS}}}"


class TreeWordRenderer(WordRenderer):
    """Returns the render tree instead of a document, to inspect fragments."""

    complete = BaseRenderer.complete


def linear(fragment: str) -> str:
    """
    OMML as linear text: a fraction is ``{num}/{den}``, a superscript
    ``{base}^{sup}``, a subscript ``{base}_{sub}``, a radical ``√{x}`` or
    ``root{n}{x}``, brackets their characters around the items, a function
    ``name␣arg``. Upright runs are marked ``'word'`` and normal text ``"text"``.
    """

    def walk(el) -> str:
        tag = el.tag.removeprefix(M)
        kids = {child.tag.removeprefix(M): child for child in el}
        if tag == "r":
            text = "".join(t.text or "" for t in el.iter(f"{M}t"))
            if el.find(f"{M}rPr/{M}nor") is not None:
                return f'"{text}"'
            if el.find(f"{M}rPr/{M}sty") is not None:
                return f"'{text}'"
            return text
        if tag == "f":
            return f"{{{walk(kids['num'])}}}/{{{walk(kids['den'])}}}"
        if tag == "sSup":
            return f"{{{walk(kids['e'])}}}^{{{walk(kids['sup'])}}}"
        if tag == "sSub":
            return f"{{{walk(kids['e'])}}}_{{{walk(kids['sub'])}}}"
        if tag == "sSubSup":
            base, sub, sup = (walk(kids[name]) for name in ("e", "sub", "sup"))
            return f"{{{base}}}_{{{sub}}}^{{{sup}}}"
        if tag == "acc":
            mark = el.find(f"{M}accPr/{M}chr").get(f"{M}val")
            return f"{{{walk(kids['e'])}}}{mark}"
        if tag == "rad":
            degree = walk(kids["deg"])
            body = walk(kids["e"])
            return f"root{{{degree}}}{{{body}}}" if degree else f"√{{{body}}}"
        if tag == "d":
            props = el.find(f"{M}dPr")

            def prop(name, default):
                found = props.find(f"{M}{name}") if props is not None else None
                return found.get(f"{M}val") if found is not None else default

            items = [walk(child) for child in el.findall(f"{M}e")]
            return f"{prop('begChr', '(')}{prop('sepChr', '|').join(items)}{prop('endChr', ')')}"
        if tag == "func":
            return f"{walk(kids['fName'])} {walk(kids['e'])}"
        if tag.endswith("Pr"):
            return ""
        return "".join(walk(child) for child in el)

    return walk(omml.to_element(fragment))


def tree(source: str, **config) -> list:
    return HandCalcs(renderer=TreeWordRenderer())(source)


def last_line(source: str) -> str:
    """The last calc line of ``source``, components joined by spaces, as linear text."""
    calcs = [item for item in tree(source) if isinstance(item, list)]
    body = calcs[-1][-1]
    return " ".join(linear(part) for part in body[-1])


# --- Identifiers ------------------------------------------------------------


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("x", "x"),
        ("x_1", "{x}_{1}"),
        ("M_max", "{M}_{'max'}"),
        ("x_a_b", "{x}_{a,b}"),
        ("N_pl_Rd", "{N}_{'pl,Rd'}"),
        ("M_Ed_y", "{M}_{'Ed',y}"),
        ("width", "'width'"),
        ("sigma", "σ"),
        ("Delta_T", "{'Δ'}_{T}"),
        ("omega_2", "{ω}_{2}"),
        ("lamb", "λ"),
        ("lambda_", "λ"),
        ("DeltaH", "'Δ'H"),
        ("ΔH", "'Δ'H"),
        ("gammaM0", "γ'M0'"),
        ("Delta__E_car", "{'Δ'' 'E}_{'car'}"),
        ("f__c", "'f c'"),
        ("a___b", "'a_b'"),
        ("x_10", "{x}_{10}"),
        ("x_hat", "{x}\u0302"),
        ("x_hat_max", "{{x}\u0302}_{'max'}"),
        ("V_dot", "{V}\u0307"),
        ("x_ddot_1", "{{x}\u0308}_{1}"),
        ("M_star", "{M}^{*}"),
        ("f_prime_c", "{f′}_{c}"),
        ("M_star_prime_Ed", "{M}_{'Ed'}^{′*}"),
    ],
)
def test_word_identifier(identifier, expected):
    assert linear(word_identifier(identifier)) == expected


def test_word_identifier_nested_style():
    nested = IdentifierOptions(subscripts="nested")
    assert linear(word_identifier("x_a_b", nested)) == "{x}_{{a}_{b}}"
    assert linear(word_identifier("N_pl_Rd", nested)) == "{N}_{{'pl'}_{'Rd'}}"


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("N_{pl,Rd}", "{N}_{'pl,Rd'}"),
        ("ΔH^{*}", "{'Δ'H}^{*}"),
        ("dot(V)", "{V}\u0307"),
        ("bar(x)_{m}", "{{x}\u0305}_{m}"),
        ("hat(sigma)'_{c}", "{{σ}\u0302′}_{c}"),
    ],
)
def test_word_identifier_symbols(spec, expected):
    options = IdentifierOptions(symbols={"s": spec})
    assert linear(word_identifier("s", options)) == expected


def test_greek_prefixes_off():
    options = IdentifierOptions(greek_prefixes=False)
    assert linear(word_identifier("DeltaH", options)) == "'DeltaH'"


def test_identifier_options_reach_the_renderer():
    source = '# hc: subscripts = "nested"\nN_pl_Rd = 2\n'
    assert last_line(source) == "{N}_{{'pl'}_{'Rd'}} = 2"
    source = "# hc: symbols = {'N_plRd': 'N_{pl,Rd}'}\nN_plRd = 2\n"
    assert last_line(source) == "{N}_{'pl,Rd'} = 2"


# The Word column of the cross-renderer tables in test_greek_identifiers.py and
# test_subscripts_and_symbols.py, keyed the same way.
GREEK_WORD = {
    "DeltaH": "'Δ'H",
    "DeltaT_max": "{'Δ'T}_{'max'}",
    "gammaM0": "γ'M0'",
    "alpha2": "α2",
    "Delta__H": "'Δ'' 'H",
    "Delta__E_car": "{'Δ'' 'E}_{'car'}",
    "ΔH": "'Δ'H",
    "Sigma_rho": "{'Σ'}_{ρ}",
    "metal": "'metal'",
    "Annual__Rate": "'Annual Rate'",
}
COMMA_WORD = {
    "N_pl_Rd": "{N}_{'pl,Rd'}",
    "f_y_k": "{f}_{y,k}",
    "M_Ed_y": "{M}_{'Ed',y}",
    "x_hat_max": "{{x}\u0302}_{'max'}",
    "M_star": "{M}^{*}",
}
NESTED_WORD = {"N_pl_Rd": "{N}_{{'pl'}_{'Rd'}}"}
SYMBOL_WORD = {"N_plRd": "{N}_{'pl,Rd'}", "dH": "{'Δ'H}^{*}"}
ACCENT_WORD = {
    "V_dot": "{V}\u0307",
    "x_ddot_1": "{{x}\u0308}_{1}",
    "V_flow": "{V}\u0307",
    "x_m": "{{x}\u0305}_{m}",
    "s_c": "{{σ}\u0302′}_{c}",
}


def test_word_tables_cover_the_shared_tables():
    from tests import test_greek_identifiers as greek
    from tests import test_subscripts_and_symbols as subs

    assert GREEK_WORD.keys() == greek.TABLE.keys()
    assert COMMA_WORD.keys() == subs.COMMA.keys()
    assert NESTED_WORD.keys() == subs.NESTED_TABLE.keys()
    assert SYMBOL_WORD.keys() == subs.SYMBOL_TABLE.keys()
    assert ACCENT_WORD.keys() == subs.ACCENT_TABLE.keys()


@pytest.mark.parametrize("identifier", [*GREEK_WORD, *COMMA_WORD])
def test_shared_identifier_tables(identifier):
    expected = {**GREEK_WORD, **COMMA_WORD}[identifier]
    assert last_line(f"{identifier} = 2\n") == f"{expected} = 2"


@pytest.mark.parametrize("identifier", NESTED_WORD)
def test_shared_nested_table(identifier):
    source = f'# hc: subscripts = "nested"\n{identifier} = 2\n'
    assert last_line(source) == f"{NESTED_WORD[identifier]} = 2"


@pytest.mark.parametrize("identifier", SYMBOL_WORD)
def test_shared_symbol_table(identifier):
    from tests.test_subscripts_and_symbols import SYMBOLS

    source = f"# hc: symbols = {SYMBOLS!r}\n{identifier} = 2\n"
    assert last_line(source) == f"{SYMBOL_WORD[identifier]} = 2"


@pytest.mark.parametrize("identifier", ACCENT_WORD)
def test_shared_accent_table(identifier):
    from tests.test_subscripts_and_symbols import ACCENT_SPECS

    source = f"# hc: symbols = {ACCENT_SPECS!r}\n{identifier} = 2\n"
    assert last_line(source) == f"{ACCENT_WORD[identifier]} = 2"


def test_upright_subscripts_are_escaped_when_merged():
    options = IdentifierOptions(symbols={"s": "N_{a<b,c&d}"})
    assert linear(word_identifier("s", options)) == "{N}_{'a<b,c&d'}"


def test_word_identifier_is_idempotent():
    once = word_identifier("M_max")
    assert word_identifier(once) == once


# --- Numbers ----------------------------------------------------------------


@pytest.mark.parametrize(
    "formatted, expected",
    [
        ("3", "3"),
        ("-3", "−3"),
        ("2.5e+05", "2.5×{10}^{5}"),
        ("1e-06", "{10}^{−6}"),
        ("-1.2e-03", "−1.2×{10}^{−3}"),
        ("inf", "∞"),
        ("-inf", "−∞"),
        ("nan", "'NaN'"),
    ],
)
def test_typeset_number(formatted, expected):
    assert linear(typeset_number(formatted)) == expected


def test_calculated_values_use_format_code():
    assert last_line("a = 1/3\n").endswith("= 0.33333")


def test_source_literals_keep_their_digits():
    assert last_line("x = 2\nb = 2.50 * x\n") == "b = 2.50⋅x = 2.50⋅2 = 5"


def test_bool_none_string_constants():
    assert last_line("a = True\n") == "a = 'True'"
    assert last_line("a = None\n") == "a = 'None'"
    assert last_line("a = 'steel'\n") == 'a = "“steel”"'


def test_complex_constant():
    assert last_line("a = 1+2j\nb = a * 1\n").endswith("= 1+2j")


def test_unit_like_values_are_text():
    class Qty:
        def __format__(self, spec):
            return "3.000 kN"

    class Text:
        def __format__(self, spec):
            return "n/a"

    # A quantity keeps its number as math and its units as normal text; a value
    # with no number form is all text.
    from handcalcs.renderers.word.handlers import render_constant
    from handcalcs.parsing.nodes import Constant

    renderer = WordRenderer()
    context = renderer.create_context()
    node = Constant(value=Qty(), calculated=True)
    assert linear(render_constant(renderer, node, context)) == '3.000" kN"'
    node = Constant(value=Text(), calculated=True)
    assert linear(render_constant(renderer, node, context)) == '"n/a"'


def test_forallpeople_quantities():
    pytest.importorskip("forallpeople")
    source = (
        "import forallpeople as si\n"
        "si.environment('structural', top_level=False)\n"
        "w = 2.5 * si.kN / si.m\n"
        "L = 3 * si.m\n"
        "M = w * L**2 / 8\n"
    )
    assert last_line(source).endswith('= 2.8125" kN·m"')


def test_pint_quantities_follow_the_registry_format():
    pint = pytest.importorskip("pint")
    ureg = pint.UnitRegistry()
    ureg.formatter.default_format = "~P"
    source = "L = 2500 * ureg.mm\nA = L**2\n"
    namespace = {"ureg": ureg}
    exec(source, namespace)
    calcs = HandCalcs(renderer=TreeWordRenderer())(source, namespace)
    line = " ".join(linear(part) for part in calcs[-1][-1][-1])
    assert line.endswith('= 6.25×{10}^{6}" mm²"')


# --- Operators --------------------------------------------------------------


def test_arithmetic_operators():
    assert last_line("a = 2\nb = 3\nc = a * b + a - b\n").startswith("c = a⋅b+a−b")


def test_division_is_a_fraction():
    assert last_line("a = 2\nb = 3\nc = (a + b) / b\n").startswith("c = {a+b}/{b}")


def test_floor_division():
    assert last_line("a = 7\nb = 2\nc = a // b\n").startswith("c = ⌊{a}/{b}⌋")


def test_modulo():
    assert last_line("a = 7\nb = 2\nc = a % b\n").startswith("c = a' mod 'b")


def test_power_and_bracketed_base():
    assert last_line("a = 2\nb = 3\nc = (a + b)**2\n").startswith("c = {(a+b)}^{2}")
    assert last_line("a = 2\nc = a**(a + 1)\n").startswith("c = {a}^{a+1}")


def test_negative_substitution_is_bracketed():
    # The leading_sign hook sees past the OMML runs.
    line = last_line("a = 2\nb = -3\nc = a * b\nd = b**2\n")
    assert line == "d = {b}^{2} = {(−3)}^{2} = 9"
    assert last_line("a = 2\nb = -3\nc = a * b\n") == "c = a⋅b = 2⋅(−3) = −6"


def test_unary_minus_and_not():
    assert last_line("a = 2\nc = -a\n") == "c = −a = −2"
    assert last_line("a = 2\nb = -3\nc = -b\n") == "c = −b = −(−3) = 3"


def test_comparisons_and_bool_ops():
    line = last_line("a = 2\nb = 3\nc = a <= b and a != b\n")
    assert line.startswith("c = a≤b' and 'a≠b")


def test_brackets_from_precedence_are_growing_delimiters():
    assert last_line("a = 2\nb = 3\nc = a * (a + b)\n").startswith("c = a⋅(a+b)")


# --- Function calls ---------------------------------------------------------


def test_sqrt_and_cbrt_are_radicals():
    assert last_line("import math\na = 4\nc = math.sqrt(a)\n").startswith("c = √{a}")
    assert last_line("import math\na = 8\nc = math.cbrt(a)\n").startswith(
        "c = root{3}{a}"
    )


def test_math_functions_are_function_names():
    assert last_line("import math\na = 1\nc = math.sin(a)\n").startswith(
        "c = 'sin' (a)"
    )
    assert last_line("import math\na = 1\nc = math.asin(a)\n").startswith(
        "c = 'arcsin' (a)"
    )


def test_floor_ceil_abs_are_brackets():
    assert last_line("import math\na = 1.5\nc = math.floor(a)\n").startswith("c = ⌊a⌋")
    assert last_line("a = -1\nc = abs(a)\n").startswith("c = |a|")


def test_user_function_arguments():
    source = "def f(x, y):\n    return x\n\na = 1\nc = f(a, 2)\n"
    assert last_line(source).startswith("c = 'f'(a,2)")


def test_method_keeps_namespace():
    source = "acc = []\nacc.append(1)\nn = len(acc)\n"
    assert last_line(source) == "n = 'len'('acc') = 'len'([1]) = 1"


def test_keyword_argument():
    source = "def f(x, days=1):\n    return x\n\na = 1\nc = f(a, days=3)\n"
    assert last_line(source).startswith("c = 'f'(a,'days'=3)")


# --- Collections and comments -----------------------------------------------


def test_collections():
    assert last_line("a = 1\nc = [a, 2]\n").startswith("c = [a,2]")
    assert last_line("a = 1\nc = (a, 2)\n").startswith("c = (a,2)")
    assert last_line("a = 1\nc = {a, 2}\n").startswith("c = {a,2}")
    assert last_line("a = 1\nc = {'k': a}\n").startswith('c = {"“k”":a}')


def test_long_collections_are_elided():
    line = last_line("a = 1\nc = [a, a, a, a, a, a, a, a, a, a, a]\n")
    assert line.startswith("c = [a,a,a,…,a,a,a]")


def test_inline_comment_is_normal_text():
    assert last_line("a = 2  # the <span> & co\n") == 'a = 2 \u2003"(the <span> & co)"'


def test_attribute_math_constant():
    assert last_line("import math\nr = 2\nA = math.pi * r**2\n").startswith(
        "A = π⋅{r}^{2}"
    )


def test_every_demo_fragment_parses():
    fragments = []

    def collect(item):
        if isinstance(item, str):
            if "<m:" in item:
                fragments.append(item)
        elif isinstance(item, (ParamsTable, CalcGrid)):
            collect(item.rows)
        elif isinstance(item, list):
            for child in item:
                collect(child)

    collect(HandCalcs(renderer=TreeWordRenderer()).demo())
    assert len(fragments) > 50
    for fragment in fragments:
        omml.to_element(fragment)
