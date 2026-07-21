from handcalcs import HandCalcs
from rich import print


def test_basic_arithmetic():
    source = """
a = 4
b = 5
c = a + b
    """
    hc = HandCalcs()
    print(hc(source))