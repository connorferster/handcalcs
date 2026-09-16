"""
End-to-end tests for PlainTextRenderer-specific rendering (symbol swaps):
superscript powers and division, which the base renderer leaves as ``**``/``/``.
"""
import pytest

from handcalcs import HandCalcs, PlainTextRenderer


@pytest.fixture
def render_plain():
    def _render(source):
        # Return the last rendered (non-empty) line for a small snippet.
        out = HandCalcs(PlainTextRenderer())(source)
        return out.splitlines()[-1]

    return _render


@pytest.mark.parametrize(
    "source,expected",
    [
        ("a=2\nb=3\ny = b**2\n", "y = b² = 3² = 9"),
        ("a=2\nb=3\ny = (a + b)**2\n", "y = (a + b)² = (2 + 3)² = 25"),
        ("b=3\nw = 2 * b**3\n", "w = 2 * b³ = 2 * 3³ = 54"),
    ],
    ids=["simple", "parenthesized-base", "nested"],
)
def test_superscript_power_has_no_stray_spaces(render_plain, source, expected):
    # A constant exponent becomes a superscript attached to the base (no "b  ²").
    assert render_plain(source) == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("a=8\nz = a / 4\n", "z = a / 4 = 8 / 4 = 2"),
        ("z = 4 / 2\n", "z = 4 / 2 = 4 / 2 = 2"),
        ("a=8\nb=3\nc=2\nz = a / (b + c)\n", "z = a / (b + c) = 8 / (3 + 2) = 1.6"),
    ],
    ids=["constant-denominator", "both-constant", "parenthesized-denominator"],
)
def test_division_keeps_slash(render_plain, source, expected):
    # Division always renders with its '/' symbol, even with constant operands.
    assert render_plain(source) == expected
