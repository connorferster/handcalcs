from handcalcs import handcalcs as hc
from collections import deque

EMPTY = deque([])

CELL_1_categorized = """CalcCell(
source=
D_1 = A + B + C
F_a = sqrt((B+A)/(C+A) + B + B + C)
G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))
H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G_a_b + B + C + B + A + B + B + A))
lines=
deque([])
"""

CELL_2_categorized = """CalcCell(
source=
Omega_3 = (F_a / D_1)
eta_xy = 0.9 * (B - A)*((2*F_a)/G_a_b - 1)*((1 - H_test_test_a)/beta_farb)**2
Psi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))
lines=
deque([])
"""

CELL_3_categorized = """ParametersCell(
source=
A = 101.01
B = 2002.002
C=30003.0003
lines=
deque([])
"""

CELL_4_categorized = """CalcCell(
source=
Psi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))
if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3); Gamma = 4 * 2
elif B > C: Delta = 5**(A/B)
lines=
deque([])
"""

CALC_1_categorized = hc.CalcLine(line=deque(['D_1', '=', 'A', '+', 'B', '+', 'C']), comment='', latex='')
CALC_2_categorized = hc.CalcLine(line=deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C'])]), comment='', latex='')
CALC_3_categorized = hc.CalcLine(line=deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])])]), comment='', latex='')
CALC_4_categorized = hc.CalcLine(line=deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G_a_b', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])]), comment='', latex='')
CALC_5_categorized = hc.CalcLine(line=deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a'])]), comment='', latex='')
CALC_6_categorized = hc.ParameterLine(line=deque(['Omega_3', '=', 0.00574378620831968]), comment='', latex='')
CALC_7_categorized = hc.CalcLine(line=deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1']), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2']), comment='', latex='')
CALC_8_categorized = hc.CalcLine(line=deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '/', deque(['2', '*', 'B', '**', '2']), '*', deque(['eta_xy', '+', 'sqrt', deque(['A', '**', '2', '+', '4', '*', deque([deque(['Omega_3', '*', 'G_a_b', '*', 'beta_farb', '**', '2']), '/', deque(['pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '+', 'G_a_b', '/', 'A'])])])]), comment='', latex='')
CALC_9_categorized = hc.ConditionalLine(condition=deque(['A', '<=', 'B', '<', 'C']), condition_type='if', expressions=deque([hc.CalcLine(line=deque(['Delta', '=', deque(['5', '*', 'A', '*', 'B', '**', '4']), '/', deque(['384', '*', 'B', '*', 'C', '**', '3']), deque(['=', 0.0003907532627942041])]), comment='', latex=''), hc.CalcLine(line=deque(['Gamma', '=', '4', '*', '2', deque(['=', 8])]), comment='', latex='')]), raw_condition='A <= B < C', raw_expression='Delta = (5*A*B**4)/(384*B*C**3); Gamma = 4 * 2', true_condition=deque([]), true_expressions=deque([]), comment='', latex='')
CALC_10_categorized = hc.ConditionalLine(condition=deque(['B', '>', 'C']), condition_type='elif', expressions=deque([hc.CalcLine(line=deque(['Delta', '=', '5', '**', deque(['A', '/', 'B']), deque(['=', 0.0003907532627942041])]), comment='', latex='')]), raw_condition='B > C', raw_expression='Delta = 5**(A/B)', true_condition=deque([]), true_expressions=deque([]), comment='', latex='')

CALC_1_w_result = hc.CalcLine(line=deque(['D_1', '=', 'A', '+', 'B', '+', 'C', deque(['=', 32106.0123])]), comment='', latex='')
CALC_2_w_result = hc.CalcLine(line=deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C']), deque(['=', 184.41007065288198])]), comment='', latex='')
CALC_3_w_result = hc.CalcLine(line=deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])]), deque(['=', 4349.7032381485815])]), comment='', latex='')
CALC_4_w_result = hc.CalcLine(line=deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G_a_b', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])]), deque(['=', 2265735022.3094497])]), comment='', latex='')
CALC_5_w_result = hc.CalcLine(line=deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a']), deque(['=', 4349.7032381485815])]), comment='', latex='')
CALC_6_w_result = hc.ParameterLine(line=deque(['Omega_3', '=', 0.00574378620831968]), comment='', latex='')
CALC_7_w_result = hc.CalcLine(line=deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1']), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2', deque(['=', -424855822363602.3])]), comment='', latex='')
CALC_8_w_result = hc.CalcLine(line=deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '/', deque(['2', '*', 'B', '**', '2']), '*', deque(['eta_xy', '+', 'sqrt', deque(['A', '**', '2', '+', '4', '*', deque([deque(['Omega_3', '*', 'G_a_b', '*', 'beta_farb', '**', '2']), '/', deque(['pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '+', 'G_a_b', '/', 'A'])])]), deque(['=', -10115.334784657554])]), comment='', latex='')
CALC_9_w_result = hc.ConditionalLine(condition=deque(['A', '<=', 'B', '<', 'C']), condition_type='if', expressions=deque([hc.CalcLine(line=deque(['Delta', '=', deque(['5', '*', 'A', '*', 'B', '**', '4']), '/', deque(['384', '*', 'B', '*', 'C', '**', '3']), deque(['=', 0.0003907532627942041]), deque(['=', 0.0003907532627942041])]), comment='', latex=''), hc.CalcLine(line=deque(['Gamma', '=', '4', '*', '2', deque(['=', 8]), deque(['=', 8])]), comment='', latex='')]), raw_condition='A <= B < C', raw_expression='Delta = (5*A*B**4)/(384*B*C**3); Gamma = 4 * 2', true_condition=deque([]), true_expressions=deque([]), comment='', latex='')
CALC_10_w_result = hc.ConditionalLine(condition=deque(['B', '>', 'C']), condition_type='elif', expressions=deque([hc.CalcLine(line=deque(['Delta', '=', '5', '**', deque(['A', '/', 'B']), deque(['=', 0.0003907532627942041]), deque(['=', 0.0003907532627942041])]), comment='', latex='')]), raw_condition='B > C', raw_expression='Delta = 5**(A/B)', true_condition=deque([]), true_expressions=deque([]), comment='', latex='')


CELL_2_converted = "hc.CalcCell(\nsource=\nOmega_3 = (F_a / D_1)\neta_xy = 0.9 * (B - A)*((2*F_a)/G_a_b - 1)*((1 - H_test_test_a)/beta_farb)**2\nPsi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))\nlines=\ndeque([ParameterLine(line=deque(['\\Omega_{3}', '=', 0.00574378620831968]), comment='', latex=''), hc.CalcLine(line=deque(['\\eta_{xy}', '=', '0.9', '\\cdot', '\\left(', 'B', '-', 'A', '\\right)', '\\cdot', '\\left(', '\\frac{', '2', '\\cdot', 'F_{a}', '}{', 'G_{a_{b}}', '}', '-', '1', '\\right)', '\\cdot', '\\left(', '\\frac{', '1', '-', 'H_{test_{test_{a}}}', '}{', '\\beta_{farb}', '}', '\\right)', '^{', '2', '}', '=', '0.9', '\\cdot', '\\left(', 2002.002, '-', 101.01, '\\right)', '\\cdot', '\\left(', '\\frac{', '2', '\\cdot', 184.41007065288198, '}{', 4349.7032381485815, '}', '-', '1', '\\right)', '\\cdot', '\\left(', '\\frac{', '1', '-', 2265735022.3094497, '}{', 4349.7032381485815, '}', '\\right)', '^{', '2', '}', '=', -424855822363602.3]), comment='', latex=''), hc.CalcLine(line=deque(['\\Psi_{45}', '=', '\\frac{', '\\Omega_{3}', '\\cdot', '\\left(', '\\pi', '\\right)', '^{', '2', '}', '\\cdot', 'A', '\\cdot', '\\left(', '\\frac{', '1', '}{', 'C', '}', '\\right)', '}{', '2', '\\cdot', '\\left(', 'B', '\\right)', '^{', '2', '}', '}', '\\cdot', '\\left(', '\\eta_{xy}', '+', '\\sqrt{', '\\left(', '\\left(', 'A', '\\right)', '^{', '2', '}', '+', '4', '\\cdot', '\\left(', '\\frac{', '\\Omega_{3}', '\\cdot', 'G_{a_{b}}', '\\cdot', '\\left(', '\\beta_{farb}', '\\right)', '^{', '2', '}', '}{', '\\left(', '\\pi', '\\right)', '^{', '2', '}', '\\cdot', 'A', '\\cdot', '\\left(', '\\frac{', '1', '}{', 'C', '}', '\\right)', '}', '+', '\\frac{', 'G_{a_{b}}', '}{', 'A', '}', '\\right)', '\\right)', '}', '\\right)', '=', '\\frac{', 0.00574378620831968, '\\cdot', '\\left(', 'pi', '\\right)', '^{', '2', '}', '\\cdot', 101.01, '\\cdot', '\\left(', '\\frac{', '1', '}{', 30003.0003, '}', '\\right)', '}{', '2', '\\cdot', '\\left(', 2002.002, '\\right)', '^{', '2', '}', '}', '\\cdot', '\\left(', -424855822363602.3, '+', '\\sqrt{', '\\left(', '\\left(', 101.01, '\\right)', '^{', '2', '}', '+', '4', '\\cdot', '\\left(', '\\frac{', 0.00574378620831968, '\\cdot', 4349.7032381485815, '\\cdot', '\\left(', 4349.7032381485815, '\\right)', '^{', '2', '}', '}{', '\\left(', 'pi', '\\right)', '^{', '2', '}', '\\cdot', 101.01, '\\cdot', '\\left(', '\\frac{', '1', '}{', 30003.0003, '}', '\\right)', '}', '+', '\\frac{', 4349.7032381485815, '}{', 101.01, '}', '\\right)', '\\right)', '}', '\\right)', '=', -10115.334784657554]), comment='', latex='')])\n"