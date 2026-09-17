source = """
## HandCalcs v2.0 Demo

# This is a demo of the main rendering features of HandCalcs v2.x. It is intended
# to showcase the output of a given renderer and make comparisons between
# renderers. This paragraph demonstrates the rendering of a series of comment lines
# which can be used for explanation within your Python script.

### The quadratic formula
from math import atan, sqrt, sin, radians, degrees
import math
# hc: -b
# The variables 'a' and 'b' below have been formatted with different line-scopes
# formatting codes. Both originally have nine decimal places.
# hc: -b
a = 5.253932023 # hc: -f .3g
b = -10.423140293 # hc: -f .5e
c = 2
x_1 = (-b + sqrt(b**2 - 4 * a * c)) / (2 * a)
x_2 = (-b - sqrt(b**2 - 4 * a * c)) / (2 * a)
f = 1; g = 2; h = 4

### Lateral torsional buckling

omega_2 = 1.0 # A beam under uniform moment
L = 6000 # Unbraced length of beam, in mm
E = 200000 # Elastic modulus, in MPa
I_y = 160E6 # Second moment of area about weak axis, in mm^4
G = 77e3 # Shear modulus, in MPa
J = 133e3 # Polar moment of area, in mm^3
C_w = 200e9 # Warping constant

#hc: -b
M_u = omega_2 * math.pi / L * sqrt(E * I_y * G * J + (math.pi * E / L)**2 * I_y * C_w) # A long equation!

### Steel section class checks
# The purpose of this demo is to show nested if/elif/else statements
b_w = 200 # mm
h_w = 310 # mm
t_f = 10 # mm
t_w = 6 # mm
F_y = 350 # MPa

if b_w / (2 * t_f) <= 145 / sqrt(F_y):
    if h_w / t_w <= 1000 / sqrt(F_y):
        class_section = 1
    elif h_w / t_w <= 1700 / sqrt(F_y):
        class_section = 2
    elif h_w / t_w <= 2400 / sqrt(F_y):
        class_section = 3
    else:
        class_section = 4
elif b_w / (2 * t_f) <= 170 / sqrt(F_y):
    if h_w / t_w <= 1700 / sqrt(F_y):
        class_section = 2
    elif h_w / t_w <= 2400 / sqrt(F_y):
        class_section = 3
    else: 
        class_section = 4
elif b_w / (2 * t_f) <= 200 / sqrt(F_y):
    if h_w / t_w <= 2400 / sqrt(F_y):
        class_section = 3
    else:
        class_section = 4
else:
    class_section = 4
    
class_section 

### Iteration using for-loops

x_values = [1, 2, 3, 4, 5]
y_values = [5, 4, 3, 2, 1]
# hc: -b
acc = [] # hc: -i
for x_value in x_values:
    for y_value in y_values:
        value_computed = degrees(atan(x_value / y_value))
        acc.append(value_computed)
acc

a_dictionary = {"cat": 1, "hat": 2, "bat": 3.14159}
a_tuple = ("string", 1.0, 42, (3 + 4j))
"""