"""
The ExcelRenderer's demo cell (``ExcelRenderer.demo_source``), used by
``HandCalcs(renderer=ExcelRenderer()).demo()``.

The general demo (``handcalcs.renderers.demo``) uses loops, collections and
imports that have no worksheet form, so it raises
``ExcelRendererIncompatibleError``. This cell is a worked steel-beam check
built to show off what does convert: inputs (``# hc: -h`` blocks and ``;``
lines), live formulas with math functions, Excel number formats, hidden and
blank rows, versioned reassignment, if/elif/else trees as ``IF`` formulas,
booleans and a text result.
"""

source = '''"""W410x60 floor beam: bending check to CSA S16 -- a live Excel worksheet made by handcalcs"""
from math import sqrt, pi

## 1. Inputs
# Yellow cells are inputs. Edit any of them in Excel and every formula on the
# sheet recalculates: this is a working spreadsheet, not a picture of one.
# hc: -h
F_y = 350  # Yield strength (MPa)
E_s = 200000  # Elastic modulus (MPa)
G = 77000  # Shear modulus (MPa)
phi = 0.9  # Resistance factor
L = 8000  # Span (mm)
L_u = 4000  # Unbraced length (mm)

### Section properties
# Each value on a ;-separated line becomes its own input row. Dimensions in mm;
# I_y and J in mm^4, C_w in mm^6, Z_x in mm^3.
b_f = 178; t_f = 12.8; t_w = 7.7; h_w = 381
I_y = 12.0e6; J = 3.28e5; C_w = 4.67e11; Z_x = 1.2e6

### Loads
# hc: -h
w_D = 6.5  # Dead load (kN/m)
w_L = 9.0  # Live load (kN/m)
alpha_D = 1.25  # Dead load factor
alpha_L = 1.5  # Live load factor

## 2. Section class
# Each if/elif/else tree becomes one live IF formula per variable; the
# symbolic column lists the cases.
if b_f / (2 * t_f) <= 145 / sqrt(F_y):
    flange_class = 1
elif b_f / (2 * t_f) <= 170 / sqrt(F_y):
    flange_class = 2
else:
    flange_class = 3
if h_w / t_w <= 1100 / sqrt(F_y):
    web_class = 1
elif h_w / t_w <= 1700 / sqrt(F_y):
    web_class = 2
else:
    web_class = 4
section_class = max(flange_class, web_class)

## 3. Factored moment
w_f = alpha_D * w_D + alpha_L * w_L  # Factored load (kN/m)
L_m = L / 1000  # hc: -p
# hc: -f .1f
M_f = w_f * L_m**2 / 8  # Simple span (kN·m)

## 4. Lateral-torsional buckling
### Elastic critical moment
omega_2 = 1.0  # Equivalent moment factor (uniform moment)
# hc: -f ,.1f
M_u = omega_2 * pi / L_u * sqrt(E_s * I_y * G * J + (pi * E_s / L_u)**2 * I_y * C_w) / 1e6  # (kN·m)
M_p = Z_x * F_y / 1e6  # Plastic moment (kN·m)
M_ratio = M_u / M_p  # hc: -i
# hc: -b
### Factored moment resistance
if M_u > 0.67 * M_p:
    M_r = 1.15 * phi * M_p * (1 - 0.28 * M_p / M_u)  # Inelastic buckling
else:
    M_r = phi * M_u  # Elastic buckling
# Reassigning a variable gives it a new versioned name on the sheet (M_r_2),
# so the row above keeps its own value.
M_r = min(M_r, phi * M_p)  # Capped at the plastic resistance (kN·m)

## 5. Check
utilization = M_f / M_r  # hc: -f .1%
passes = utilization <= 1 and section_class <= 2
if passes:
    status = "OK"
else:
    status = "NOT OK"
'''
