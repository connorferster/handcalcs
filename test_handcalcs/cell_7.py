from math import asin, sin, sqrt

# Short
a = 23
b = 43
c = 52

f = c / a + b  # Comment
g = c * f / a  # Comment
d = (
    sqrt(a / b)
    + asin(sin(b / c))
    + (a / b) ** (0.5)
    + sqrt((a * b + b * c) / (b**2))
    + sin(a / b)
)  # Comment

calc_results = globals()
