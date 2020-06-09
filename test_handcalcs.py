import handcalcs as hc
import json

A = 101.01
B = 2002.002
C = 30003.0003

CALC_1 = "D_1 = A + B + C"
CALC_2 = "F_a = sqrt((B+A)/(C+A) + B + B + C)"
CALC_3 = "G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
CALC_4 = "H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G + B + C + B + A + B + B + A))"
CALC_5 = "beta_farb = min(G_a_b, H_test_test_a)"
CALC_6 = "Omega_3 = (F_a / D_1)"
CALC_7 = "eta_xy = 0.9 * (B - A)*(((2*F_a)/G_a_b - 1))*((1 - H_test_test_a/beta_farb))**2"
CALC_8 = "Psi_45 = (Omega_3 * pi**2 * A * (1/C))) / (2 * B**2) *  (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))"
CALC_9 = "if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3)"

CELL_1 = "\n".join([CALC_1, CALC_2, CALC_3, CALC_4])
CELL_2 = "\n".join([CALC_6, CALC_7, CALC_8])
CELL_3 = "\#Parameters\nA = 101.01\nB = 2002.002\nC=30003.0003"
CELL_4 = "\n".join([CALC_8, CALC_9])


def load_calcs():
    A = 101.01
    B = 2002.002
    C = 30003.0003

    CALC_1 = "D_1 = A + B + C"
    CALC_2 = "F_a = sqrt((B+A)/(C+A) + B + B + C)"
    CALC_3 = "G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
    CALC_4 = "H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G + B + C + B + A + B + B + A))"
    CALC_5 = "beta_farb = min(G_a_b, H_test_test_a)"
    CALC_6 = "Omega_3 = (F_a / D_1)"
    CALC_7 = "eta_xy = 0.9 * (B - A)*(((2*F_a)/G_a_b - 1))*((1 - H_test_test_a/beta_farb))**2"
    CALC_8 = "Psi_45 = (Omega_3 * pi**2 * A * (1/C))) / (2 * B**2) *  (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))"
    CALC_9 = "if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3)"

    CELL_1 = "\n".join([CALC_1, CALC_2, CALC_3, CALC_4])
    CELL_2 = "\n".join([CALC_6, CALC_7, CALC_8])
    CELL_3 = "\#Parameters\nA = 101.01\nB = 2002.002\nC=30003.0003"
    CELL_4 = "\n".join([CALC_8, CALC_9])

    exec(CALC_1)
    exec(CALC_2)
    exec(CALC_3)
    exec(CALC_4)
    exec(CALC_5)
    exec(CALC_6)
    exec(CALC_7)
    exec(CALC_8)
    exec(CALC_9)
    return locals()


CALC_RESULTS = load_calcs()

def test_raw_python_to_separated_dict():
    assert hc.raw_python_to_separated_dict(CELL_1, CALC_RESULTS) = """
    {0: {'line': deque(['D_1', '=', 'A', '+', 'B', '+', 'C']), 'type': 'normal calc', 'comment': ''}, 1: {'line': deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C'])]), 'type': 'long calc', 'comment': ''}, 2: {'line': deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])])]), 'type': 'long calc', 'comment': ''}, 3: {'line': deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])]), 'type': 'long calc', 'comment': ''}}
    """
