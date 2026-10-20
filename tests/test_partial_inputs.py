"""
Partial inputs: binding input values into a calculation script
(handcalcs.parsing.inputs and HandCalcs(..., inputs=...)).
"""

import pathlib
import re
from fractions import Fraction

import pint

import pytest

from handcalcs import HandCalcs, PlainTextRenderer, find_inputs
from handcalcs.parsing.inputs import RESOLVER, InputBinding, bind_inputs
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.markdown import MarkdownRenderer

UNITS = """import pint
ureg = pint.UnitRegistry()
m = ureg.m
kN = ureg.kN
kPa = kN / m**2
"""


def rhs(source: str, name: str) -> str:
    """The right-hand side of the first line assigning ``name``."""
    for statement in source.replace(";", "\n").splitlines():
        target, _, value = statement.partition("=")
        if target.strip() == name:
            return value.split("#")[0].strip()
    raise AssertionError(f"{name} is not assigned")


# --- Number times units: only the number is replaced -------------------------


@pytest.mark.parametrize(
    "line, value, expected",
    [
        ("L = 6 * m", 8, "8 * m"),
        ("w = 4.5 * kN / m", 6.2, "6.2 * kN / m"),
        ("p = -12 * kPa", -15, "-15 * kPa"),
        ("p = 12 * kPa", -15, "-15 * kPa"),
        ("A = 0.25 * m**2", 0.5, "0.5 * m**2"),
        ("w = kN / m * 4.5", 6.2, "kN / m * 6.2"),
        ("w = ureg.kN * 4.5", 6.2, "ureg.kN * 6.2"),
        ("phi = 0.9", 0.85, "0.85"),
        ("E = 200 * kPa", "steel", "'steel'"),
        ("E = 200 * kPa", [1, 2], "[1, 2]"),
        ("n = 3", True, "True"),
    ],
)
def test_bound_values(line, value, expected):
    name = line.split("=")[0].strip()
    bound = bind_inputs(UNITS + line + "\n", {name: value})
    assert rhs(bound, name) == expected


def test_number_in_divisor_is_not_a_magnitude():
    # Replacing the 4 in kN / 4 would not scale the value by the input
    with pytest.raises(ValueError, match="computed"):
        bind_inputs(UNITS + "w = kN / 4\n", {"w": 2})


def test_script_variable_is_not_a_unit():
    source = UNITS + "a = 2 * m\nb = 2 * a\n"
    with pytest.raises(ValueError, match="'b' is computed on line 7"):
        bind_inputs(source, {"b": 3})


def test_alias_of_a_variable_is_a_variable():
    source = UNITS + "a = 2 * m\nb = 3 * m\nc = a * b\nd = 3 * c\n"
    with pytest.raises(ValueError, match="'d' is computed"):
        bind_inputs(source, {"d": 1})


def test_allow_computed_replaces_whole_value():
    source = UNITS + "a = 2 * m\nb = 2 * a\n"
    bound = bind_inputs(source, {"b": 3}, allow_computed=True)
    assert rhs(bound, "b") == "3"


# --- Which assignment is bound ------------------------------------------------


def test_first_binding_only_and_reassignment_runs():
    source = "L = 6\nL = L + 1\n"
    bound = bind_inputs(source, {"L": 8})
    assert bound == "L = 8\nL = L + 1\n"


def test_params_line():
    bound = bind_inputs("a = 1; b = 2; c = 3\n", {"a": 10, "c": 30})
    assert bound == "a = 10; b = 2; c = 30\n"


def test_trailing_comment_kept():
    bound = bind_inputs(UNITS + "w = 4.5 * kN / m  # line load\n", {"w": 6})
    assert bound.endswith("w = 6 * kN / m  # line load\n")


def test_non_ascii_text_before_the_value():
    # Node offsets are UTF-8 byte offsets
    bound = bind_inputs("φ = 0.9; σ_ü = 1.5 # ünits\n", {"σ_ü": 2.5, "φ": 0.8})
    assert bound == "φ = 0.8; σ_ü = 2.5 # ünits\n"


def test_multiline_value():
    source = "xs = [\n    1,\n    2,\n]\ny = 1\n"
    assert bind_inputs(source, {"xs": [3], "y": 2}) == "xs = [3]\ny = 2\n"


def test_crlf_line_endings():
    source = "a = 1\r\nb = 2\r\n"
    assert bind_inputs(source, {"b": 3}) == "a = 1\r\nb = 3\r\n"


@pytest.mark.parametrize(
    "source",
    [
        "if True:\n    a = 1\n",
        "for a in range(2):\n    pass\n",
        "def f():\n    a = 1\n",
        "a, b = 1, 2\n",
        "a = b = 1\n",
    ],
)
def test_unbindable_assignment(source):
    with pytest.raises(ValueError, match="cannot be bound"):
        bind_inputs(source, {"a": 3})


def test_augmented_assignment_after_binding_runs():
    assert bind_inputs("a = 1\na += 1\n", {"a": 5}) == "a = 5\na += 1\n"


# --- Unknown inputs and unwritable values -------------------------------------


def test_unknown_input_raises():
    with pytest.raises(KeyError, match="'q'"):
        bind_inputs("a = 1\n", {"a": 2, "q": 1})


def test_unknown_input_ignored_when_not_strict():
    assert bind_inputs("a = 1\n", {"a": 2, "q": 1}, strict=False) == "a = 2\n"


@pytest.mark.parametrize("value", [object(), float("nan"), {1, 2}.__iter__()])
def test_value_without_literal_raises(value):
    with pytest.raises(TypeError, match="cannot be written as a Python literal"):
        bind_inputs("a = 1\n", {"a": value})


def test_no_inputs_leaves_source_unchanged():
    source = UNITS + "w = 4.5 * kN / m\n"
    assert bind_inputs(source, {}) == source


# --- find_inputs --------------------------------------------------------------


def test_find_inputs():
    source = UNITS + (
        "w = -4.5 * kN / m  # load\n"
        "L = 6 * m; φ = 0.9\n"
        'grade = "350W"\n'
        "xs = [1, 2]\n"
        "M = w * L**2 / 8\n"
        "L = L + 1 * m\n"
    )
    assert find_inputs(source) == {
        "w": -4.5,
        "L": 6,
        "φ": 0.9,
        "grade": "350W",
        "xs": [1, 2],
    }


def test_find_inputs_from_path(tmp_path):
    path = tmp_path / "calc.py"
    path.write_text("a = 1\nb = a * 2\n", encoding="utf-8")
    assert find_inputs(path) == {"a": 1}


def test_find_inputs_round_trip():
    # find_inputs gives a template that bind_inputs accepts unchanged
    source = UNITS + "w = 4.5 * kN / m\nL = 6 * m\nM = w * L**2 / 8\n"
    assert bind_inputs(source, find_inputs(source)) == source


# --- HandCalcs(..., inputs=...) -------------------------------------------------


def without_addresses(rendered: str) -> str:
    """The render with object addresses (the pint registry's repr) blanked out."""
    return re.sub(r"0x[0-9a-fA-F]+", "0x", rendered)


BEAM = UNITS + (
    "## Simply supported beam\n"
    "w = 4.5 * kN / m  # line load\n"
    "L = 6 * m; φ = 0.9\n"
    "M_f = w * L**2 / 8\n"
    "M_r = φ * M_f\n"
)


@pytest.mark.parametrize(
    "renderer", [PlainTextRenderer, LatexRenderer, MarkdownRenderer, HTMLRenderer]
)
def test_render_with_inputs_matches_edited_source(renderer):
    # Rendering with inputs is the same as rendering the script with the numbers
    # typed in
    edited = BEAM.replace("4.5 * kN", "6.2 * kN").replace("6 * m;", "8 * m;")
    hc = HandCalcs(renderer())
    assert without_addresses(hc(BEAM, inputs={"w": 6.2, "L": 8})) == without_addresses(
        hc(edited)
    )


def test_render_with_inputs_recomputes_results():
    out = HandCalcs(PlainTextRenderer())(BEAM, inputs={"w": 6.2, "L": 8})
    assert "w = 6.2 * kN / m" in out
    assert "L = 8" in out
    assert (
        "M_f = w * L² / 8 = 6.2 kilonewton / meter * 8 meter² / 8 = 49.6 kilonewton * meter"
        in out
    )
    assert "4.5" not in out


def test_render_with_inputs_from_path(tmp_path):
    path = tmp_path / "beam.py"
    path.write_text(BEAM, encoding="utf-8")
    hc = HandCalcs(PlainTextRenderer())
    assert without_addresses(hc(pathlib.Path(path), inputs={"L": 8})) == (
        without_addresses(hc(BEAM, inputs={"L": 8}))
    )


def test_render_inputs_with_supplied_globals_raises():
    with pytest.raises(TypeError, match="supplied_globals"):
        HandCalcs(PlainTextRenderer())("a = 1\n", {"a": 1}, inputs={"a": 2})


def test_render_strict_and_allow_computed_pass_through():
    hc = HandCalcs(PlainTextRenderer())
    out = hc(
        "a = 1\nb = 2 * a\n", inputs={"b": 5, "q": 0}, strict=False, allow_computed=True
    )
    assert "b = 5" in out


# --- Object inputs: quantities and other objects ------------------------------

# A registry of the caller's, separate from the one each script makes
ureg = pint.UnitRegistry()


class Section:
    """An object with no literal form, assigned to the script as it is."""

    def __init__(self, area):
        self.area = area

    def __str__(self):
        return f"Section({self.area})"


def bound_source(source: str, inputs: dict, **kwargs) -> str:
    """The source as it is shown, after running it with ``inputs``."""
    binding = InputBinding(source, inputs, **kwargs)
    namespace = dict(binding.namespace())
    exec(binding.exec_source, namespace)
    return binding.parse_source(namespace)


@pytest.mark.parametrize(
    "line, value, expected",
    [
        ("w = 4.5 * kN / m", 6200 * ureg.N / ureg.m, "w = 6.2 * kN / m"),
        ("L = 6 * m", 8000 * ureg.mm, "L = 8 * m"),  # an int stays an int
        ("p = -12 * kPa", -15000 * ureg.Pa, "p = -15 * kPa"),
        ("A = 2.0 * m**2", 15000 * ureg.cm**2, "A = 1.5 * m**2"),
        ("w = (4.5 * kN\n     / m)", 7 * ureg.kN / ureg.m, "w = (7.0 * kN\n     / m)"),
    ],
)
def test_quantity_converted_to_the_line_units(line, value, expected):
    name = line.split(" = ")[0]
    assert bound_source(UNITS + line + "\n", {name: value}) == UNITS + expected + "\n"


def test_quantity_in_incompatible_units_raises():
    with pytest.raises(ValueError, match="cannot be converted to the units of line 7"):
        HandCalcs(PlainTextRenderer())(BEAM, inputs={"w": 6 * ureg.m})


def test_numbers_of_other_types_are_written_as_numbers():
    # e.g. numpy.float64, or a value from a pandas row
    assert bind_inputs("a = 1\nb = 2\n", {"a": Fraction(1, 2), "b": True}) == (
        "a = 0.5\nb = True\n"
    )


@pytest.mark.parametrize(
    "line, value, shown",
    [
        ("A = 100", Section(250), "Section(250)"),  # no literal form
        ("A = 100", Fraction(1, 3), "0.33333"),  # not exactly a float
        ("A = 100 * m", Section(250), "Section(250)"),  # cannot be divided by units
        ("A = 100", 0.5 * ureg.m, "0.5 meter"),  # a quantity on a line without units
    ],
)
def test_object_assigned_as_it_is(line, value, shown):
    out = HandCalcs(PlainTextRenderer())(
        UNITS + line + "\nB = A\n", inputs={"A": value}
    )
    assert f"A = {shown}\nB = A = {shown}\n" in out
    assert "hc-input" not in out


def test_object_reaches_the_calculation():
    source = "A = 100\nB = A.area * 2\n"
    out = HandCalcs(PlainTextRenderer())(source, inputs={"A": Section(250)})
    assert "B = A.area * 2 = 250 * 2 = 500" in out


def test_object_on_a_computed_line_needs_allow_computed():
    source = "a = 1\nb = 2 * a\n"
    with pytest.raises(ValueError, match="allow_computed"):
        HandCalcs(PlainTextRenderer())(source, inputs={"b": Section(1)})
    out = HandCalcs(PlainTextRenderer())(
        source, inputs={"b": Section(1)}, allow_computed=True
    )
    assert "b = Section(1)" in out


def test_object_input_leaves_no_resolver_in_the_namespace():
    binding = InputBinding("A = 100\n", {"A": Section(1)})
    namespace = dict(binding.namespace())
    exec(binding.exec_source, namespace)
    binding.parse_source(namespace)
    assert RESOLVER not in namespace
    assert namespace["A"].area == 1


def test_bind_inputs_refuses_objects():
    with pytest.raises(TypeError, match="HandCalcs"):
        bind_inputs(UNITS + "L = 6 * m\n", {"L": 8000 * ureg.mm})


@pytest.mark.parametrize(
    "renderer", [PlainTextRenderer, LatexRenderer, MarkdownRenderer, HTMLRenderer]
)
def test_render_with_quantities_matches_numbers(renderer):
    # A quantity renders as its number in the script's units would
    hc = HandCalcs(renderer())
    quantities = {"w": 6200 * ureg.N / ureg.m, "L": 8000 * ureg.mm}
    assert without_addresses(hc(BEAM, inputs=quantities)) == without_addresses(
        hc(BEAM, inputs={"w": 6.2, "L": 8})
    )


@pytest.mark.parametrize(
    "renderer", [PlainTextRenderer, LatexRenderer, MarkdownRenderer, HTMLRenderer]
)
def test_render_object_in_every_renderer(renderer):
    out = HandCalcs(renderer())("A = 100\nB = A\n", inputs={"A": Section(250)})
    assert "Section(250)" in out
    assert "hc-input" not in out
