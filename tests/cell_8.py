from math import asin, sin, sqrt

a = 23
V_dot = 43
c = 52

f = c / a + V_dot  # Comment
g = c * f / a  # Comment
d = sqrt(a / V_dot+ asin(sin(V_dot / c))+ (a / V_dot) ** (0.5)+ sqrt((a * V_dot + V_dot * c) / (V_dot**2))+ sin(a / V_dot)) # Comment

calc_results = globals()
