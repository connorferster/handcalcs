import handcalcs as hc
from collections import deque

EMPTY = deque([])

CELL_1_categorized = """CalcCell(
source=
D_1 = A + B + C
F_a = sqrt((B+A)/(C+A) + B + B + C)
G_a_b = (B+B+A)/((C+A+A)/(C+B+sin(A)))
H_test_test_a = sqrt((B+A+B+C+A+B)/(B+C+B+C+B) +B*A*B*C*B * sqrt(B + G_a_b + B + C + B + A + B + B + A))
incoming_lines=
deque([])
outgoing_lines=deque([])"""

CELL_2_categorized = """CalcCell(
source=
Omega_3 = (F_a / D_1)
eta_xy = 0.9 * (B - A)*(((2*F_a)/G_a_b - 1))*((1 - H_test_test_a)/beta_farb)**2
Psi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))
incoming_lines=
deque([])
outgoing_lines=deque([])"""

CELL_3_categorized = """ParametersCell(
source=
#Parameters
A = 101.01
B = 2002.002
C=30003.0003
incoming_lines=
deque([])
outgoing_lines=
deque([])"""

CELL_4_categorized = """CalcCell(
source=
Psi_45 = (Omega_3 * pi**2 * A * (1/C)) / (2 * B**2) * (eta_xy + sqrt(A**2 + 4*((Omega_3 * G_a_b * beta_farb**2)/(pi**2*A*(1/C)) + G_a_b / A)))
if A <= B < C: Delta = (5*A*B**4)/(384*B*C**3)
elif B > C: Delta = 5**(A/B)
incoming_lines=
deque([])
outgoing_lines=deque([])"""

CALC_1_categorized = hc.CalcLine(line=deque(['D_1', '=', 'A', '+', 'B', '+', 'C']), comment='')
CALC_2_categorized = hc.CalcLine(line=deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C'])]), comment='')
CALC_3_categorized = hc.CalcLine(line=deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])])]), comment='')
CALC_4_categorized = hc.CalcLine(line=deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G_a_b', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])])]), comment='')
CALC_5_categorized = hc.CalcLine(line=deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a'])]), comment='')
CALC_6_categorized = hc.ParameterLine(line=deque(['Omega_3', '&=', 0.00574378620831968]), comment='')
CALC_7_categorized = hc.CalcLine(line=deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1'])]), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2']), comment='')
CALC_8_categorized = hc.CalcLine(line=deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '/', deque(['2', '*', 'B', '**', '2']), '*', deque(['eta_xy', '+', 'sqrt', deque(['A', '**', '2', '+', '4', '*', deque([deque(['Omega_3', '*', 'G_a_b', '*', 'beta_farb', '**', '2']), '/', deque(['pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '+', 'G_a_b', '/', 'A'])])])]), comment='')
CALC_9_categorized = hc.ConditionalLine(condition=deque(['A', '<=', 'B', '<', 'C']), expressions=deque([deque(['Delta', '=', deque(['5', '*', 'A', '*', 'B', '**', '4']), '/', deque(['384', '*', 'B', '*', 'C', '**', '3'])])]), raw_condition='A <= B < C', raw_expression='Delta = (5*A*B**4)/(384*B*C**3)', condition_type = 'if', true_condition = EMPTY, true_expressions = EMPTY, comment='')
CALC_10_categorized = hc.ConditionalLine(condition=deque(['B', '>', 'C']), expressions=deque([deque(['Delta', '=', '5', '**', deque(['A', '/', 'B'])])]), raw_condition='B > C', raw_expression='Delta = 5**(A/B)', condition_type = 'elif', true_condition = EMPTY, true_expressions = EMPTY, comment='')

CALC_1_w_result = hc.CalcLine(line=deque(['D_1', '=', 'A', '+', 'B', '+', 'C', deque(['=', 32106.0123])]), comment='')
CALC_2_w_result = hc.CalcLine(line=deque(['F_a', '=', 'sqrt', deque([deque(['B', '+', 'A']), '/', deque(['C', '+', 'A']), '+', 'B', '+', 'B', '+', 'C']), deque(['=', 184.41007065288198])]), comment='')
CALC_3_w_result = hc.CalcLine(line=deque(['G_a_b', '=', deque(['B', '+', 'B', '+', 'A']), '/', deque([deque(['C', '+', 'A', '+', 'A']), '/', deque(['C', '+', 'B', '+', 'sin', deque(['A'])])]), deque(['=', 4349.7032381485815])]), comment='')
CALC_4_w_result = hc.CalcLine(line=deque(['H_test_test_a', '=', 'sqrt', deque([deque(['B', '+', 'A', '+', 'B', '+', 'C', '+', 'A', '+', 'B']), '/', deque(['B', '+', 'C', '+', 'B', '+', 'C', '+', 'B']), '+', 'B', '*', 'A', '*', 'B', '*', 'C', '*', 'B', '*', 'sqrt', deque(['B', '+', 'G_a_b', '+', 'B', '+', 'C', '+', 'B', '+', 'A', '+', 'B', '+', 'B', '+', 'A'])]), deque(['=', 2265735022.3094497])]), comment='')
CALC_5_w_result = hc.CalcLine(line=deque(['beta_farb', '=', 'min', deque(['G_a_b', ',', 'H_test_test_a']), deque(['=', 4349.7032381485815])]), comment='')
CALC_6_w_result = hc.ParameterLine(line=deque(['Omega_3', '&=', 0.00574378620831968]), comment='')
CALC_7_w_result = hc.CalcLine(line=deque(['eta_xy', '=', '0.9', '*', deque(['B', '-', 'A']), '*', deque([deque([deque(['2', '*', 'F_a']), '/', 'G_a_b', '-', '1'])]), '*', deque([deque(['1', '-', 'H_test_test_a']), '/', 'beta_farb']), '**', '2', deque(['=', -424855822363602.3])]), comment='')
CALC_8_w_result = hc.CalcLine(line=deque(['Psi_45', '=', deque(['Omega_3', '*', 'pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '/', deque(['2', '*', 'B', '**', '2']), '*', deque(['eta_xy', '+', 'sqrt', deque(['A', '**', '2', '+', '4', '*', deque([deque(['Omega_3', '*', 'G_a_b', '*', 'beta_farb', '**', '2']), '/', deque(['pi', '**', '2', '*', 'A', '*', deque(['1', '/', 'C'])]), '+', 'G_a_b', '/', 'A'])])]), deque(['=', -10115.334784657554])]), comment='')
CALC_9_w_result = hc.ConditionalLine(condition=deque(['A', '<=', 'B', '<', 'C']), expressions=deque([deque(['Delta', '=', deque(['5', '*', 'A', '*', 'B', '**', '4']), '/', deque(['384', '*', 'B', '*', 'C', '**', '3']), deque(['=', 0.0003907532627942041])])]), raw_condition='A <= B < C', raw_expression='Delta = (5*A*B**4)/(384*B*C**3)', condition_type = 'if', true_condition = EMPTY, true_expressions = EMPTY, comment='')
CALC_10_w_result = hc.ConditionalLine(condition=deque(['B', '>', 'C']), expressions=deque([deque(['Delta', '=', '5', '**', deque(['A', '/', 'B']), deque(['=', 0.0003907532627942041])])]), raw_condition='B > C', raw_expression='Delta = 5**(A/B)', condition_type = 'elif', true_condition = EMPTY, true_expressions = EMPTY, comment='')

