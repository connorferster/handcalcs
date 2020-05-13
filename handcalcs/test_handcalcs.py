import handcalcs as hc
from math import sqrt, sin, pi
from collections import deque
import json

from . import test_results as results

A = 101.01
B = 2002.002
C = 30003.0003


CALC_1 = "D_1 = A + B + C"
CALC_2 = "F_a = sqrt((B+A)/(C+A) + B + B + C)"
CALC_3 = "G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
CALC_4 = "H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G + B + C + B + A + B + B + A))"
CALC_5 = "beta_farb = min(G_a_b, H_test_test_a)"
CALC_6 = "Omega_3 = (F_a / D_1)"
CALC_7 = (
    "eta_xy = 0.9 * (B - A)*(((2*F_a)/G_a_b - 1))*((1 - H_test_test_a)/beta_farb)**2"
)
CALC_8 = "Psi_45 = (Omega_3 * pi**2 * A * (1/C))) / (2 * B**2) *  (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))"
CALC_9 = "if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3)"
CALC_10 = "elif B > C: Delta = 5**(A/B)"

CALC_1_D =  deque(['D_1', '=', 'A', '+', 'B', '+', 'C'])
CALC_2_D =  deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C'])])
CALC_3_D =  deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])])])
CALC_4_D =  deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])])
CALC_5_D =  deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a'])])
CALC_6_D =  deque(['Omega_3', '=', deque(['F_a', '/', 'D_1'])])
CALC_7_D =  deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1'])]), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2'])
CALC_8_D =  deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])])])


CELL_1 = "\n".join([CALC_1, CALC_2, CALC_3, CALC_4])
CELL_2 = "\n".join([CALC_6, CALC_7, CALC_8])
CELL_3 = "#Parameters\nA = 101.01\nB = 2002.002\nC=30003.0003"
CELL_4 = "\n".join([CALC_8, CALC_9, CALC_10])


def load_calcs():
    A = 101.01
    B = 2002.002
    C = 30003.0003

    CALC_1 = "D_1 = A + B + C"
    CALC_2 = "F_a = sqrt((B+A)/(C+A) + B + B + C)"
    CALC_3 = "G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))"
    CALC_4 = "H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G_a_b + B + C + B + A + B + B + A))"
    CALC_5 = "beta_farb = min(G_a_b, H_test_test_a)"
    CALC_6 = "Omega_3 = (F_a / D_1)"
    CALC_7 = (
    "eta_xy = 0.9 * (B - A)*(((2*F_a)/G_a_b - 1))*((1 - H_test_test_a)/beta_farb)**2"
    )
    CALC_8 = "Psi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))"
    CALC_9 = "if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3)"
    CALC_10 = "elif B > C: Delta = 5**(A/B)"

    CELL_1 = "\n".join([CALC_1, CALC_2, CALC_3, CALC_4])
    CELL_2 = "\n".join([CALC_6, CALC_7, CALC_8])
    CELL_3 = "#Parameters\nA = 101.01\nB = 2002.002\nC=30003.0003"
    CELL_4 = "\n".join([CALC_8, CALC_9, CALC_10])

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
globals().update(CALC_RESULTS)


def test_categorize_line():
    assert hc.categorize_line(CALC_1, CALC_RESULTS) == results.CALC_1_categorized
    assert hc.categorize_line(CALC_2, CALC_RESULTS) == results.CALC_2_categorized
    assert hc.categorize_line(CALC_3, CALC_RESULTS) == results.CALC_3_categorized
    assert hc.categorize_line(CALC_4, CALC_RESULTS) == results.CALC_4_categorized
    assert hc.categorize_line(CALC_5, CALC_RESULTS) == results.CALC_5_categorized
    assert hc.categorize_line(CALC_6, CALC_RESULTS) == results.CALC_6_categorized
    assert hc.categorize_line(CALC_7, CALC_RESULTS) == results.CALC_7_categorized
    assert hc.categorize_line(CALC_8, CALC_RESULTS) == results.CALC_8_categorized
    assert hc.categorize_line(CALC_9, CALC_RESULTS) == results.CALC_9_categorized
    assert hc.categorize_line(CALC_10, CALC_RESULTS) == results.CALC_10_categorized

def test_categorize_raw_cell():
    assert str(hc.categorize_raw_cell(CELL_1, CALC_RESULTS)) == results.CELL_1_categorized
    assert str(hc.categorize_raw_cell(CELL_2, CALC_RESULTS)) == results.CELL_2_categorized
    assert str(hc.categorize_raw_cell(CELL_3, CALC_RESULTS)) == results.CELL_3_categorized
    assert str(hc.categorize_raw_cell(CELL_4, CALC_RESULTS)) == results.CELL_4_categorized

def test_add_result_values_to_line():
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_1, CALC_RESULTS), CALC_RESULTS) == results.CALC_1_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_2, CALC_RESULTS), CALC_RESULTS) == results.CALC_2_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_3, CALC_RESULTS), CALC_RESULTS) == results.CALC_3_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_4, CALC_RESULTS), CALC_RESULTS) == results.CALC_4_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_5, CALC_RESULTS), CALC_RESULTS) == results.CALC_5_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_6, CALC_RESULTS), CALC_RESULTS) == results.CALC_6_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_7, CALC_RESULTS), CALC_RESULTS) == results.CALC_7_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_8, CALC_RESULTS), CALC_RESULTS) == results.CALC_8_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_9, CALC_RESULTS), CALC_RESULTS) == results.CALC_9_w_result
    assert hc.add_result_values_to_line(hc.categorize_line(CALC_10, CALC_RESULTS), CALC_RESULTS) == results.CALC_10_w_result


def test_format_conditional_lines():
    assert hc.format_conditional_lines("A > B") == "&\\textrm{Since, }A > B:\\\\\n"
    assert hc.format_conditional_lines("15 >= x >= 30") == "&\\textrm{Since, }15 >= x >= 30:\\\\\n"

def test_format_calc_lines():
    assert hc.format_calc_lines("V = A + 23 = 43 + 23 = 76") == "V &= A + 23 = 43 + 23 &= 76\n"
    assert hc.format_calc_lines("G_h = \\frac{1 + A }{2 \\cdot \\left(1 + A\\right)} = \\frac{1 + 23 }{2 \\cdot \\left(1 + 23 \\right)} = 0.5") == "G_h &= \\frac{1 + A }{2 \\cdot \\left(1 + A\\right)} = \\frac{1 + 23 }{2 \\cdot \\left(1 + 23 \\right)} &= 0.5\n"

def test_swap_values():
    assert hc.swap_values(deque(["=", "A", "+", 23]), {"A": 43}) == deque(["=", 43, "+", 23])
    assert hc.swap_values(deque(["eta", "=", "beta", "+", "theta"]), {"eta": 3, "beta": 2, "theta": 1}) == deque([3, "=", 2, "+", 1])

def test_swap_for_greek():
    assert hc.swap_for_greek(deque(["eta", "=", "beta", "+", "theta"])) == deque(["\\eta", "=", "\\beta", "+", "\\theta"])
    assert hc.swap_for_greek(deque(["M_r", "=", "phi", "\\cdot", deque(["psi", "\\cdot", "F_y"])])) == deque(["M_r", "=", "\\phi", "\\cdot", deque(["\\psi", "\\cdot", "F_y"])])
    assert hc.swap_for_greek(deque(["lamb", "=", 3])) == deque(["\\lambda", "=", 3])


def test_swap_superscripts():
    assert hc.swap_superscripts(CALC_8_D) == deque(['Psi_45', '=', deque(['Omega_3', '*', '\\left(', 'pi', '\\right)', '^{', '2', '}', '*', 'A', '*', deque(['1', '/', 'C'])])])
    assert hc.swap_superscripts(CALC_7_D) == deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1'])]), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '^{', '2', '}'])


def test_swap_py_operators():
    assert hc.swap_py_operators(CALC_4_D) == deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '\\cdot', 'A', '\\cdot', 'B', '\\cdot', 'C', '\\cdot', 'B', '\\cdot', 'sqrt', deque(['B', '+', 'G', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])])
    assert hc.swap_py_operators(CALC_7_D) == deque(['eta_xy', '=', '0.9', '\\cdot', deque(['B', '-', 'A']), '\\cdot', deque([deque([deque(['2', '\\cdot', 'F_a']), '/', 'G_a_b', '-', '1'])]), '\\cdot', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2'])
    assert hc.swap_py_operators(CALC_8_D) == deque(['Psi_45', '=', deque(['Omega_3', '\\cdot', 'pi', '**', '2', '\\cdot', 'A', '\\cdot', deque(['1', '/', 'C'])])])
    # TODO: Add test for swapping % and \bmod

CALC_1_D =  deque(['D_1', '=', 'A', '+', 'B', '+', 'C'])
CALC_2_D =  deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C'])])
CALC_3_D =  deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])])])
CALC_4_D =  deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])])
CALC_5_D =  deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a'])])
CALC_6_D =  deque(['Omega_3', '=', deque(['F_a', '/', 'D_1'])])
CALC_7_D =  deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1'])]), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2'])
CALC_8_D =  deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])])])

def swap_math_funcs():
    assert hc.swap_math_funcs(CALC_5_D) == deque(['beta_farb', '=', '\\operatorname{min}', deque(['G_a_b', ',', 'H_test_test_a'])])
    assert hc.swap_math_funcs(CALC_3_D) == deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', '\\sin', deque(['A'])])])])