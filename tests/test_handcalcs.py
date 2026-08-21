from handcalcs import HandCalcs
from rich import print


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
    hc = HandCalcs()
    print(hc(source))
    assert False


def test_scripting():
    source = """
from math import sqrt, pi
def circle_area(diam: float) -> float:
    return pi * diam**2 / 4

radius = 5
area = circle_area(2 * radius)
    """
    hc = HandCalcs()
    print(hc(source))
    assert False