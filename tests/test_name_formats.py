"""
A value keeps the ``# hc: -f`` format code of the line that calculated it on the
lines that substitute it, unless such a line has an ``-f`` of its own; and the ASCII
renderer spaces comparison operators like the arithmetic ones.
"""

from handcalcs import HandCalcs
from handcalcs.renderers.ascii import ASCIIRenderer
from handcalcs.renderers.latex import LatexRenderer

PREFIX = "C_f = 500\nC_r = 600.3\nDCR = C_f / C_r  # hc: -f .3f\n"


def lines(source: str) -> list[str]:
    return [line.strip() for line in HandCalcs(ASCIIRenderer())(source).splitlines()]


def test_check_line_uses_the_format_of_the_name():
    out = lines(PREFIX + "ok = DCR <= 1.0  # hc: --check\n")
    assert out[2] == "DCR = C_f / C_r = 500.000 / 600.300 = 0.833"
    assert out[3] == "ok = DCR <= 1.0 = 0.833 <= 1.0 ✓"


def test_later_calc_uses_the_format_of_the_name():
    # The name's format applies where it is substituted; the line's own result
    # keeps the line's format.
    assert lines(PREFIX + "x = DCR * 2\n")[3] == "x = DCR * 2 = 0.833 * 2 = 1.6658"


def test_own_format_code_wins():
    assert (
        lines(PREFIX + "y = DCR * 3  # hc: -f .1f\n")[3]
        == "y = DCR * 3 = 0.8 * 3 = 2.5"
    )


def test_reassignment_without_a_format_code_forgets_it():
    out = lines(PREFIX + "DCR = DCR * 1.1\nz = DCR + 1\n")
    assert out[3] == "DCR = DCR * 1.1 = 0.83292 * 1.1 = 0.91621"
    assert out[4] == "z = DCR + 1 = 0.91621 + 1 = 1.9162"


def test_standalone_format_code_is_unchanged():
    # A standalone -f is the section's format, not a name's: it applies as before.
    out = lines("# hc: -f .2f\na = 1 / 3\nb = a * 3\n")
    assert out == ["a = 1 / 3 = 0.33", "b = a * 3 = 0.33 * 3 = 1.00"]


def test_param_line_format_carries():
    out = lines("a = 5.253932023  # hc: -f .3g\nb = a * 2\n")
    assert out == ["a = 5.25", "b = a * 2 = 5.25 * 2 = 10.508"]


def test_name_format_in_latex():
    rendered = HandCalcs(LatexRenderer())(PREFIX + "ok = DCR <= 1.0  # hc: --check\n")
    assert "\\mathrm{DCR} \\le 1.0 = 0.833 \\le 1.0" in rendered


def test_each_render_starts_afresh():
    hc = HandCalcs(ASCIIRenderer())
    hc(PREFIX)
    assert hc("DCR = 0.123456\nx = DCR * 1\n").splitlines()[1].strip() == (
        "x = DCR * 1 = 0.12346 * 1 = 0.12346"
    )


def test_name_format_with_mode_num():
    # Without the symbolic column, no renderer rule has rewritten the name first.
    rendered = HandCalcs(LatexRenderer())(
        PREFIX + 'x = DCR * 2  # hc: mode = "ass num res"\n'
    )
    assert "x &= 0.833 \\cdot 2" in rendered


def test_ascii_comparisons_are_spaced():
    out = lines("a = 2\nb = a > 1\nc = 1 < a <= 5\nd = a == 2\ne = a != 3\n")
    assert out[1:] == [
        "b = a > 1 = 2 > 1 = True",
        "c = 1 < a <= 5 = 1 < 2 <= 5 = True",
        "d = a == 2 = 2 == 2 = True",
        "e = a != 3 = 2 != 3 = True",
    ]
