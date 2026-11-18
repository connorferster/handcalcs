"""
``# hc: -u``: a number times units (``P = 5 * kN``) shows as its value alone
(``P = 5 kN``) instead of ``5 * kN = 5 * 1 kN = 5 kN`` (#353).
"""

import pytest

from handcalcs import HandCalcs, config
from handcalcs.renderers import ASCIIRenderer

forallpeople = pytest.importorskip("forallpeople")


def plain(line: str) -> str:
    """
    How ``line`` (``R = 7 * kN``) renders without ``-u``: forallpeople 4 shows
    a unit as ``kN``, so the substitution repeats the line and is dropped;
    earlier versions show it as ``1 kN``.
    """
    target, expression = line.split(" = ")
    number, unit = expression.split(" * ")
    if repr(getattr(forallpeople, unit)) == unit:
        return f"{line} = {number} {unit}"
    return f"{line} = {number} * 1 {unit} = {number} {unit}"


def render(source: str, namespace: dict) -> list[str]:
    exec(source, namespace)
    return HandCalcs(ASCIIRenderer()).render_run(source, namespace).splitlines()


@pytest.fixture
def fap() -> dict:
    si = forallpeople
    # Other tests load other environments; this one defines kN.
    si.environment("structural")
    return {"si": si, "kN": si.kN, "m": si.m, "mm": si.mm}


@pytest.fixture
def ureg():
    pint = pytest.importorskip("pint")
    return pint.UnitRegistry()


@pytest.mark.parametrize(
    "line, shown",
    [
        ("P = 5 * kN", "P = 5 kN"),
        ("P = -12 * kN", "P = -12 kN"),
        ("w = 4.5 * kN / m", "w = 4.5 kN/m"),
        ("A = 300 * mm**2", "A = 300 mm²"),
        ("s = 2.5 * si.kPa", "s = 2.5 kPa"),
        ("P = kN * 5", "P = 5 kN"),
    ],
)
def test_number_times_units_collapses(fap, line, shown):
    assert render(f"# hc: -u\n{line}\n", fap) == [shown]


@pytest.mark.parametrize(
    "line",
    [
        "X = 5 * kN * 2",
        "Y = 3 * m + 200 * mm",
        "Z = 1 / (5 * m)",
        "Q = (5 * kN)**2",
    ],
)
def test_other_lines_keep_their_working(fap, line):
    target = line.split(" = ")[0]
    out = render(f"# hc: -u\n{line}\n", fap)
    assert out[0].startswith(f"{target} = {line.split(' = ')[1].split()[0]}")
    assert out[0].count("=") >= 2


def test_calculations_keep_their_working(fap):
    out = render("# hc: -u\nw = 4.5 * kN / m\nL = 6 * m\nM = w * L**2 / 8\n", fap)
    assert out[-1] == "M = w * L² / 8 = 4.5 kN/m * (6 m)² / 8 = 20.25 kN·m"


def test_a_variable_of_one_unit_is_not_a_unit(fap):
    # F is 1 kN, like kN itself: only its name tells them apart.
    out = render("# hc: -u\nF = 1 * kN\nR = 3 * F\n", fap)
    assert out == ["F = 1 kN", "R = 3 * F = 3 * 1 kN = 3 kN"]


def test_standalone_command_lasts_until_turned_off(fap):
    source = "# hc: -u\nP = 5 * kN\n\nQ = 6 * kN\n# hc: units = False\nR = 7 * kN\n"
    assert render(source, fap) == [
        "P = 5 kN",
        "Q = 6 kN",
        plain("R = 7 * kN"),
    ]


def test_inline_command_applies_to_its_line(fap):
    out = render("P = 5 * kN  # hc: -u\nQ = 6 * kN\n", fap)
    assert out == ["P = 5 kN", plain("Q = 6 * kN")]


def test_off_without_the_command(fap):
    assert render("P = 5 * kN\n", fap) == [plain("P = 5 * kN")]


def test_symbolic_only_mode_is_left_alone(fap):
    # A collapsed line shows only its value, which this mode hides.
    out = render("# hc: mode = 'ass sym'\n# hc: -u\nP = 5 * kN\n", fap)
    assert out == ["P = 5 * kN"]


def test_config_option_turns_it_on_everywhere(fap, tmp_path, monkeypatch):
    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "config.json"))
    config.reset_config()
    config.set_option("units", True)
    try:
        assert render("P = 5 * kN\n", fap) == ["P = 5 kN"]
    finally:
        config.reset_config()


def test_pint(ureg):
    namespace = {"ureg": ureg, "kN": ureg.kN, "m": ureg.m}
    out = render("# hc: -u\nP = 5 * kN\nw = 4.5 * kN / m\nc = 2 * ureg.kPa\n", namespace)
    assert out == ["P = 5 kilonewton", "w = 4.5 kilonewton / meter", "c = 2 kilopascal"]


def test_pint_quantity_is_not_a_unit(ureg):
    namespace = {"F": 1 * ureg.kN}
    out = render("# hc: -u\nR = 3 * F\n", namespace)
    assert len(out[0].split(" = ")) == 4


def test_jupyter_variable_from_an_earlier_cell_is_not_a_unit(fap):
    IPython = pytest.importorskip("IPython")
    import importlib
    import sys

    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    shell = InteractiveShell.instance()
    sys.modules.pop("handcalcs.interfaces.jupyter", None)
    importlib.import_module("handcalcs.interfaces.jupyter")
    try:
        shell.user_ns.update(fap)
        shell.run_cell("F = 1 * kN")
        config.set_option("jupyter_renderer", "ascii")
        with capture_output() as captured:
            shell.run_cell_magic("render", "", "# hc: -u\nP = 5 * kN\nR = 3 * F\n")
        text = captured.outputs[0].data["text/plain"]
        assert "P = 5 kN" in text
        assert "R = 3 * F = 3 * 1 kN = 3 kN" in text
    finally:
        config.reset_option("jupyter_renderer")
        sys.modules.pop("handcalcs.interfaces.jupyter", None)
        InteractiveShell.clear_instance()
