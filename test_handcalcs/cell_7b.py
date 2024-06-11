from math import asin, sin, sqrt

# Short
alpha_zeta = 9.84e-1
b_prime_c = 43
causal = 4.2 + 3.2j

f = causal / alpha_zeta + b_prime_c  # Comment
g = causal * f / alpha_zeta  # Comment
d = (
    sqrt(alpha_zeta / b_prime_c)
    + sum((1, 2, 3))
    + (alpha_zeta / b_prime_c) ** (0.5)
    + sqrt((alpha_zeta * b_prime_c + b_prime_c) / (1.23e3**2))
    + sin(alpha_zeta / b_prime_c)
)  # Comment

calc_results = globals()
