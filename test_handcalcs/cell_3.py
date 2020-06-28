from math import ceil, sqrt
from scipy.integrate import quad

def F(x):
    return x**2 + 3*x

y = -2
b = 3
c  = 4
alpha_eta_psi = 23
d = sqrt(1 / (b / c))
f = ceil((alpha_eta_psi + 1) % 2)
g = quad(F,y,b)

calc_results = globals()




