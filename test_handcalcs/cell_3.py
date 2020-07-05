from math import ceil, sqrt
def quad(*args, **kwargs):
    """
    This is a mocked integration function to mimic
    scipy.integrate.quad. It doesn't do anything
    other than return a value in the correct format.
    """
    return (42, 0.001)

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




