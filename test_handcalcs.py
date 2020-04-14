import pytest
from math import sqrt, pi, sin

A = 101.01
B = 2002.002
C = 30003.0003

CALC_1 = "D_1 = A + B + C"
CALC_2 = "F_a = sqrt((B+A)/(C+A) + B + B + C)"
CALC_3 = "G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
CALC_4 = "H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G + B + C + B + A + B + B + A))"
CELL_1 = "\n".join([CALC_1, CALC_2, CALC_3, CALC_4])

CELL_2 = """
    A = 101.01
    B = 2002.002
    C=30003.0003"""


def load_calcs():
    A = 101.01
    B = 2002.002
    C = 30003.0003

    CALC_1 = "D = A + B + C"
    CALC_2 = "F = sqrt((B+A)/(C+A) + B + B + C)"
    CALC_3 = "G = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
    CALC_4 = "H = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B+A+B+C+B + sqrt(B + G + B + C + B + A + B + B + A))"

    exec(CALC_1)
    exec(CALC_2)
    exec(CALC_3)
    exec(CALC_4)
    return locals()


CALC_RESULTS = load_calcs()

def test