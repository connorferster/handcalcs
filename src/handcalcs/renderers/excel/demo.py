"""
An Excel-compatible demo cell for the ExcelRenderer.

The base demo (``handcalcs.renderers.demo``) uses loops, collections and
imports that have no worksheet equivalent, so it raises
``ExcelRendererIncompatibleError``. This source sticks to what the renderer
supports: math functions, reassignment, logical tests, an if/elif/else
tree and the comment commands.
"""

source = '''"""W410x60 beam check (CSA S16), Excel demo"""
from math import sqrt, pi
## Section and material
# Inputs are on a yellow fill: change one in Excel and the sheet recalculates.
# hc: -h
F_y = 350  # Yield strength (MPa)
E_s = 200000  # Elastic modulus (MPa)
G = 77000  # Shear modulus (MPa)
phi = 0.9  # Resistance factor
L_u = 4000  # Unbraced length (mm)
I_y = 12.0e6  # Weak-axis moment of inertia (mm4)
J = 3.28e5  # St. Venant torsion constant (mm4)
C_w = 4.67e11  # Warping constant (mm6)
Z_x = 1.2e6  # Plastic section modulus (mm3)
h_w = 381  # Web height (mm)
t_w = 7.7  # Web thickness (mm)

## Web class
# The class is a live IF formula: edit t_w and it changes.
if h_w / t_w <= 1100 / sqrt(F_y):
    web_class = 1
elif h_w / t_w <= 1700 / sqrt(F_y):
    web_class = 2
else:
    web_class = 4

## Lateral-torsional buckling
### Elastic critical moment
omega_2 = 1.0  # Uniform moment
# hc: -f ,.0f
M_u = omega_2 * pi / L_u * sqrt(E_s * I_y * G * J + (pi * E_s / L_u)**2 * I_y * C_w) / 1e6  # kN·m
M_p = Z_x * F_y / 1e6  # Plastic moment (kN·m)
# hc: -b
### Factored resistance
# hc: -f .1f
ratio = M_u / M_p  # hc: -i
M_r = 1.15 * phi * M_p * (1 - 0.28 * M_p / M_u)  # Inelastic range
M_r = min(M_r, phi * M_p)  # Capped at the plastic resistance

## Check
M_f = 260  # Factored moment (kN·m)
utilization = M_f / M_r
passes = utilization <= 1 and web_class <= 2
'''
