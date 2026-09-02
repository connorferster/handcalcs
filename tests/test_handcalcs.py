"""
End-to-end smoke tests for the full HandCalcs pipeline
(source -> parser -> HcSequence -> default PlainTextRenderer).

These guard the wiring between the layers and pin current rendered output.
Node- and BaseRenderer-level behavior is covered in the dedicated unit
modules; here we only assert that a realistic script renders coherently.
"""
from handcalcs import HandCalcs


def test_basic_arithmetic():
    source = """
from math import sqrt, pi
alpha = 4
beta = 5 # Inline comment
# Comment
d = 3
# hc: cat = "hat"
c = (d * (alpha + beta)) / pi # hc: -f .4g
e = sqrt(beta**2 - alpha**2) # hc: -i
if e <= 3:
    if 2 < beta < alpha:
        f = 12
    elif 2 < alpha < beta:
        f = 20
    else:
        f = 30
    """
    out = HandCalcs()(source)

    assert out == (
        "[Python import]: from math import sqrt, pi\n"
        "α = 4\n"
        "β = 5 (Inline comment)\n"
        "Comment\n"
        "d = 3\n"
        "c = ((d)(α + β)) / (π) = ((3)(4 + 5)) / (3.142) = 8.594\n"
        "Since (e<=3) -> (3.0<=3) is True:\n"
        "    Since (2<α<β) -> (2<4<5) is True:\n"
        "        f = 20\n"
    )
    # The `# hc: -i` (ignore) line must be suppressed from the output.
    assert "e =" not in out
    # Only the satisfied elif branch renders; the others do not.
    assert "f = 12" not in out
    assert "f = 30" not in out


def test_scripting():
    source = """
from math import sqrt, pi
def circle_area(diam: float) -> float:
    return pi * diam**2 / 4

radius = 5
area = circle_area(2 * radius)
    """
    out = HandCalcs()(source)

    assert out == (
        "[Python import]: from math import sqrt, pi\n"
        "radius = 5\n"
        "area =  circle_area((2)(radius))  =  circle_area((2)(5))  = 78.54\n"
    )
