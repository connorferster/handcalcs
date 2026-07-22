from handcalcs import HandCalcs
from rich import print


def test_basic_arithmetic():
    source = """
a = 4
b = 5
d = 3
c = (d * (a + b)) / 2
    """
    hc = HandCalcs()
    print(hc(source))
    assert False