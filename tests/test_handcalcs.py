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
e = sqrt(beta**2 - alpha**2)
if e <= 3:
    if 2 < beta < alpha:
        f = 12
    elif 2 < alpha < beta:
        f = 20
    else:
        f = 30
    """
    print(source)
    hc = HandCalcs()
    rendered = hc(source)
    print(rendered)
    expected = (
        "[Python import]: from math import sqrt, pi\n\n"
        "alpha = 4\n"
        "beta = 5 (Inline comment)\n"
        "Comment\n"
        "d = 3\n"
        "c = d * (alpha + beta) / pi = 3 * (4 + 5) / 3.142 = 8.594\n"
        "e =  sqrt(beta ** 2 - alpha ** 2)  =  sqrt(5 ** 2 - 4 ** 2)  = 3\n"
        "Since (e<=3) -> (3<=3) is True:\n"
        "    Since (2<alpha<beta) -> (2<4<5) is True:\n"
        "        f = 20\n"
    )
    assert rendered == expected


def test_line_break_command():
    # The line-break command ('-b'/'--line-break') inserts a single blank line
    # in the rendered output on the line after it occurs, both as a standalone
    # comment command and as an inline comment command on a calc line. It must
    # not leak a blank line onto any subsequent line.
    source = """
a = 1
# hc: -b
b = 2
c = 3 # hc: -b
d = 4
"""
    rendered = HandCalcs()(source)
    expected = (
        "a = 1\n"
        "\n"          # standalone '# hc: -b'
        "b = 2\n"
        "c = 3\n"
        "\n"          # inline 'c = 3 # hc: -b'
        "d = 4\n"
    )
    assert rendered == expected