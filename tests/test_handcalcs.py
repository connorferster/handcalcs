"""
End-to-end smoke tests for the full HandCalcs pipeline
(source -> parser -> HcSequence -> default PlainTextRenderer).

These guard the wiring between the layers and pin current rendered output.
Node- and BaseRenderer-level behavior is covered in the dedicated unit
modules; here we only assert that a realistic script renders coherently.
"""
from handcalcs import HandCalcs, PlainTextRenderer


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
    out = HandCalcs(PlainTextRenderer())(source)

    assert out == (
        "[Python import]: from math import sqrt, pi\n"
        "α = 4\n"
        "β = 5 (Inline comment)\n"
        "Comment\n"
        "d = 3\n"
        "c = d * (α + β) / π = 3 * (4 + 5) / 3.142 = 8.594\n"
        "Since (e<=3) -> (3<=3) is True:\n"
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
    out = HandCalcs(PlainTextRenderer())(source)

    assert out == (
        "[Python import]: from math import sqrt, pi\n"
        "radius = 5\n"
        "area = circle_area(2 * radius) = circle_area(2 * 5) = 78.54\n"
    )


import pytest
from handcalcs.renderers import get_renderer


@pytest.mark.parametrize("renderer", ["base", "plain_text", "html", "latex", "markdown"])
def test_non_numeric_values_ignore_format_code(renderer):
    # date.__format__ passes the spec to strftime, so applying the default
    # '.5g' format code would render the code itself instead of the date.
    source = (
        "import datetime\nd = datetime.date(2020, 1, 2) # hc: -f .3f\n"
        "e = datetime.date(2021, 3, 4)\nx = 3.14159265\n"
    )
    out = str(HandCalcs(renderer=get_renderer(renderer)())(source))
    assert "2020-01-02" in out and "2021-03-04" in out
    assert ".3f" not in out and ".5g" not in out
    assert "3.1416" in out


KWARGS_SOURCE = (
    "import datetime\nn = 3\nt = datetime.timedelta(days=n, hours=2)\n"
    "def f(a, b=1, **kw):\n    return a + b\nopts = {'b': 2}\nr = f(1, **opts)\n"
)


@pytest.mark.parametrize("renderer", ["plain_text", "html"])
def test_function_call_keyword_arguments_are_rendered(renderer):
    out = str(HandCalcs(renderer=get_renderer(renderer)())(KWARGS_SOURCE))
    assert (
        "t = datetime.timedelta(days=n, hours=2)"
        " = datetime.timedelta(days=3, hours=2) = 3 days, 2:00:00"
    ) in out
    assert "r = f(1, **opts) = f(1, **{b: 2}) = 3" in out


def test_mode_drop_aliases_from_comment_commands():
    # An inline `# hc: mode=...` applies to its own line only; a standalone one
    # persists until another command changes it.
    source = (
        "a = 2\nb = 3\n"
        "c = a + b  # hc: mode='no_num'\n"
        "d = a * b  # hc: mode='no_sym'\n"
        "e = a - b\n"
        "# hc: mode='drop_numeric'\n"
        "f = a + b\n"
        "# hc: mode='full'\n"
        "g = a + b\n"
    )
    lines = HandCalcs(PlainTextRenderer())(source).splitlines()
    assert "c = a + b = 5" in lines
    assert "d = 2 * 3 = 6" in lines
    assert "e = a - b = 2 - 3 = -1" in lines
    assert "f = a + b = 5" in lines
    assert "g = a + b = 2 + 3 = 5" in lines
