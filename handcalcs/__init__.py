"""
Calculates compressive resistance due to flexural buckling in doubly symmetric
shapes.

CSA S16-14 Cl. 13.3.1
"""

from math import sqrt, pi

def main(A, F_y, n, E, K, L, r, phi = 0.9):
    F_e = (pi**2 * E) / (((K * L) / (r))**2)
    lamb = sqrt(F_y / F_e)
    C_r = (phi * A * F_y) / ((1 + lamb**(2*n)) ** (1/n))
    return locals()
