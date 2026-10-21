"""
Items S2-S12 of the v2.0rc1 release review (rc1_release_review.md): Python that
rendered as nothing or as garbage, and defaults that surprised.
"""
import io

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

TEXT_RENDERERS = [ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer]


def ascii(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


def latex(source: str) -> str:
    return HandCalcs(LatexRenderer())(source)


def word_xml(source: str) -> str:
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    document = HandCalcs(WordRenderer())(source)
    document.save(io.BytesIO())
    return document.element.xml


# --- S2: generator expressions and comprehension filters ------------------------

XS = "xs = [1, 2, 3]\n"


def test_generator_expression_as_the_only_argument():
    assert "s = sum(x² for x in xs) = 14" in ascii(XS + "s = sum(x**2 for x in xs)\n")
    assert (
        "s &= \\operatorname{sum}\\left(x^{2}\;\\mathrm{for}\;x\;\\mathrm{in}\;\\mathrm{xs}\\right) = 14"
        in latex(XS + "s = sum(x**2 for x in xs)\n")
    )


def test_generator_expression_beside_other_arguments_keeps_its_brackets():
    assert "max((x for x in xs), default=0) = 3" in ascii(
        XS + "t = max((x for x in xs), default=0)\n"
    )


def test_comprehension_filters():
    out = ascii(XS + "ys = [x * 2 for x in xs if x > 1 if x < 3]\n")
    assert "ys = [x * 2 for x in xs if x>1 if x<3] = [4]" in out
    assert "\;\\mathrm{if}\;x > 1" in latex(XS + "g = list(x for x in xs if x > 1)\n")


def test_comprehension_with_several_targets():
    out = ascii(XS + "ps = {i: x for i, x in enumerate(xs)}\n")
    assert "{i: x for i, x in enumerate(xs)}" in out


@pytest.mark.parametrize("renderer_class", TEXT_RENDERERS)
def test_generator_expression_renders(renderer_class):
    out = HandCalcs(renderer_class())(XS + "s = sum(x for x in xs if x > 1)\n")
    assert "sum" in out and "5" in out


def test_generator_expression_in_word():
    assert ">for<" in word_xml(XS + "s = sum(x**2 for x in xs)\n").replace(" ", "")


# --- S3: an attribute of an expression ---------------------------------------------

UNITS = "import pint  # hc: -i\nureg = pint.UnitRegistry()  # hc: -i\nL = 6 * ureg.m\n"


def test_attribute_of_an_expression():
    pytest.importorskip("pint")
    out = ascii(UNITS + "v = (L * 2).magnitude\n")
    assert "v = (L * 2).magnitude = (6 meter * 2).magnitude = 12" in out
    out = latex(UNITS + "v = (L * 2).magnitude\n")
    assert "v &= \\left(L \\cdot 2\\right).\\mathrm{magnitude}" in out


def test_attribute_of_a_call():
    pytest.importorskip("pint")
    assert "w = L.to(\"mm\").magnitude + 1 = 6001" in ascii(UNITS + 'w = L.to("mm").magnitude + 1\n')


def test_attribute_of_an_expression_in_word():
    pytest.importorskip("pint")
    assert "magnitude" in word_xml(UNITS + "v = (L * 2).magnitude\n")


def test_attribute_of_an_expression_in_excel():
    pytest.importorskip("xlsxwriter")
    from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError

    with pytest.raises(ExcelRendererIncompatibleError, match="of an expression"):
        HandCalcs(ExcelRenderer())("a = 2.5\nb = (a * 2).real\n")


# --- S4: f-strings and lambdas -----------------------------------------------------


def test_f_string_shows_its_value():
    assert 's = "a=3"' in ascii('a = 3\ns = f"a={a}"\n')
    assert 't = "3.00 kN"' in ascii('a = 3\nt = f"{a:.2f} kN"\n')
    assert 's &= \\text{``a=3\'\'}' in latex('a = 3\ns = f"a={a}"\n')


def test_f_string_with_a_call_is_not_evaluated_again():
    # A user function may have side effects, so it is not called again: the
    # line shows the value the assignment gave its target.
    source = (
        "calls = []\n"
        "def f(v):\n"
        "    calls.append(v)\n"
        "    return v * 2\n"
        's = f"{f(2)} kN"\n'
        "n = len(calls)\n"
    )
    out = ascii(source)
    assert 's = "4 kN"' in out
    assert "n = len(calls) = len([2]) = 1" in out


def test_lambda_shows_only_its_source():
    out = ascii("x = 100\nf = lambda x: x * 2\ny = f(3)\n")
    assert "f = lambda x: x * 2\n" in out
    assert "0x" not in out
    assert "y = f(3) = 6" in out


def test_lambda_parameters_are_not_substituted():
    out = ascii("v = 100\nz = sorted([3, 1, 2], key=lambda v: -v)\n")
    assert "z = sorted([3, 1, 2], key=lambda v: -v) = [3, 2, 1]" in out


def test_lambda_with_starred_parameters():
    out = ascii("g = lambda alpha, *rest, **kw: alpha + len(rest)\n")
    assert "g = lambda α, *rest, **kw: α + len(rest)" in out


def test_lambda_in_latex_and_word():
    assert "f &= \\mathrm{lambda}\;x\\colon\;x \\cdot 2" in latex("f = lambda x: x * 2\n")
    assert "lambda" in word_xml("f = lambda x: x * 2\n")


# --- S5: integers keep their digits under a general format code ---------------------


def test_integers_keep_their_digits():
    out = ascii("E = 200000\nN = 10**12\nn = 7 // 2\n")
    assert "E = 200000" in out
    assert "N = 10¹² = 1000000000000" in out
    assert "n = 7 // 2 = 3" in out
    assert "N &= 10^{12} = 1000000000000" in latex("N = 10**12\n")


def test_floats_keep_the_general_format():
    assert "P = 1.2346e+06" in ascii("P = 1234567.891\n")


def test_explicit_format_codes_apply_to_integers():
    assert "N = 10⁶ = 1.000e+06" in ascii("N = 10**6  # hc: -f .3e\n")
    assert "N = 10⁶ = 1000000.00" in ascii("N = 10**6  # hc: -f .2f\n")
    assert "N = 10⁶ = 1,000,000" in ascii("N = 10**6  # hc: -f ,.3g\n")


@pytest.mark.parametrize(
    "value, format_code, expected",
    [
        (200000, ".5g", "d"),
        (200000, ",.3g", ",d"),
        (200000, "n", "n"),
        (200000, ".2f", ".2f"),
        (2.5, ".5g", ".5g"),
        (True, ".5g", ".5g"),
    ],
)
def test_value_format_code(value, format_code, expected):
    from handcalcs.renderers.base import value_format_code

    assert value_format_code(value, format_code) == expected


def test_numpy_and_pint_integers():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pint")
    from handcalcs.renderers.base import value_format_code

    assert value_format_code(np.int64(200000), ".5g") == "d"
    out = ascii(UNITS.replace("L = 6 * ureg.m\n", "") + "F = 250000 * ureg.N\n")
    assert "F = 250000 * ureg.N = 250000 * newton = 250000 newton" in out


# --- S7a: a call of a module's function made for its effect is skipped --------------


def test_setup_calls_are_skipped():
    pytest.importorskip("forallpeople")
    out = ascii(
        "import forallpeople as si\n"
        "# Set up the units\n"
        'si.environment("structural")\n'
        "import numpy as np\n"
        "np.random.seed(1)\n"
        "L = 6 * si.m\n"
    )
    assert "environment" not in out and "seed" not in out
    assert "Set up the units" in out  # the comment above is kept, as for print()
    assert "L = 6 * si.m" in out


def test_pure_module_calls_and_methods_and_user_functions_are_kept():
    source = (
        "import math\n"
        "math.sqrt(4)\n"
        "acc = []\n"
        "acc.append(2)\n"
        "def check(v):\n"
        "    return v < 1\n"
        "check(0.5)\n"
    )
    out = ascii(source)
    assert "√(4) = 2" in out
    assert "acc.append(2)" in out
    assert "check(0.5)" in out


def test_setup_calls_produce_no_excel_error():
    pytest.importorskip("xlsxwriter")
    pytest.importorskip("forallpeople")
    from handcalcs.renderers.excel import ExcelRenderer

    HandCalcs(ExcelRenderer())(
        'import forallpeople as si\nsi.environment("structural")\nL = 6 * si.m\n'
    )


# --- S7b: strings in quotes ---------------------------------------------------------


def test_strings_are_quoted_in_ascii():
    out = ascii('name = "W310x39"\nloads = {"dead": 5}\nw = loads["dead"]\n')
    assert 'name = "W310x39"' in out
    assert 'loads = {"dead": 5}' in out
    assert 'w = loads["dead"] = 5' in out


def test_method_names_are_not_quoted():
    pytest.importorskip("pint")
    out = ascii(UNITS + 'M = (L * 2).to("mm")\n')
    assert 'M = (L * 2).to("mm") = (6 meter * 2).to("mm") = 12000 millimeter' in out


def test_strings_are_quoted_and_escaped_in_html():
    out = HandCalcs(HTMLRenderer())('name = "<b>W310</b>"\n')
    assert "name = “&lt;b&gt;W310&lt;/b&gt;”" in out


def test_ascii_superscripts_are_not_quoted():
    assert "y = b² = 3² = 9" in ascii("b = 3\ny = b**2\n")


# --- S9: numpy arrays ---------------------------------------------------------------

NP = "import numpy as np  # hc: -i\n"


def test_array_elements_take_the_format_code():
    pytest.importorskip("numpy")
    out = ascii(NP + "x = np.array([1.23456, 2.34567])  # hc: -f .2f\n")
    assert "x = np.array([1.23456, 2.34567]) = [1.23, 2.35]" in out


def test_two_dimensional_arrays_are_matrices():
    pytest.importorskip("numpy")
    source = NP + "M = np.array([[1, 2], [3, 4]])\nB = M @ M\n"
    assert "B = M @ M = [[1, 2], [3, 4]] @ [[1, 2], [3, 4]] = [[7, 10], [15, 22]]" in ascii(source)
    assert "= \\begin{bmatrix} 7 & 10 \\\\ 15 & 22 \\end{bmatrix}" in latex(source)
    html = HandCalcs(HTMLRenderer())(source)
    assert '<span class="hc-matrix-cell">22</span>' in html
    assert "<m:m>" in word_xml(source)


def test_large_matrices_are_shortened():
    pytest.importorskip("numpy")
    out = latex(NP + "big = np.arange(1.0, 151.0).reshape(15, 10)\n")
    assert "\\vdots & \\vdots" in out
    assert "141 & 142" in out


def test_numpy_scalars_and_indexing():
    pytest.importorskip("numpy")
    out = ascii(NP + "M = np.array([[1, 2], [3, 4]])\nr = M[0]\ns = np.float64(2.5) * 2\n")
    assert "r = M[0] = [1, 2]" in out
    assert "s = np.float64(2.5) * 2 = 5" in out


# --- S11: defaults --------------------------------------------------------------------


def test_bare_handcalcs_renders_ascii(tmp_path, monkeypatch):
    import handcalcs

    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "hc_config.json"))
    handcalcs.reset_config()
    assert HandCalcs()("a = 1\nb = a * 2\n") == "a = 1\nb = a * 2 = 1 * 2 = 2\n"


def test_decorator_without_a_renderer(tmp_path, monkeypatch):
    import handcalcs
    from handcalcs import handcalc

    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "hc_config.json"))
    handcalcs.reset_config()

    @handcalc
    def bare(a):
        b = a * 2
        return b

    @handcalc()
    def called(a):
        b = a * 3
        return b

    assert bare(2) == (4, "b = a * 2 = 2 * 2 = 4\n")
    assert called(2) == (6, "b = a * 3 = 2 * 3 = 6\n")

    handcalcs.set_option("default_renderer", "latex")
    try:
        @handcalc()
        def latex_calc(a):
            b = a * 3
            return b

        assert "\\begin{aligned}" in latex_calc(2)[1]
    finally:
        handcalcs.reset_config()
