"""
forallpeople's ``si.environment(..., top_level=True)`` puts its units in
``builtins``. A bare unit in a formula substitutes its value, found there as
Python finds it, instead of rendering as nothing.
"""
import builtins

import pytest

from handcalcs import HandCalcs, ASCIIRenderer
from handcalcs.renderers.latex import LatexRenderer

si = pytest.importorskip("forallpeople")

SOURCE = """\
import forallpeople as si
si.environment("structural", top_level=True)
a = 2
b = a * m
d = kN
e = a * kN / m
"""


@pytest.fixture
def restore_builtins():
    """Undo the units the source's top_level=True writes to builtins."""
    saved = dict(vars(builtins))
    yield
    # forallpeople removes the units it put in builtins itself, on its next
    # environment() call; anything left over is then removed here.
    si.environment("default", top_level=False)
    for name in set(vars(builtins)) - set(saved):
        delattr(builtins, name)
    vars(builtins).update(saved)


def test_bare_units_substitute_in_ascii(restore_builtins):
    rendered = HandCalcs(ASCIIRenderer())(SOURCE)
    assert "b = a * m = 2 * 1 m = 2 m" in rendered
    assert "d = kN = 1 kN" in rendered
    assert "e = a * kN / m = 2 * 1 kN / 1 m = 2 kN/m" in rendered


def test_bare_units_substitute_in_latex(restore_builtins):
    rendered = HandCalcs(LatexRenderer())(SOURCE)
    assert r"b &= a \cdot m = 2 \cdot 1.000 m = 2.000 m" in rendered
    assert r"d &= \mathrm{kN} = 1.000 kN" in rendered
    assert (
        r"e &= \frac{a \cdot \mathrm{kN}}{m} = \frac{2 \cdot 1.000 kN}{1.000 m}"
        r" = 2.000 kN/m"
    ) in rendered
