from test_handcalcs.function_mocks import euler_buckling_load
from math import sqrt
from test_handcalcs.function_mocks import E, I_x, k_x, L, area, I_y, k_y, f_y, n, phi


F_e_x = euler_buckling_load(E, I_x, k_x, L) / area
F_e_y = euler_buckling_load(E, I_y, k_y, L) / area
F_e = min(F_e_x, F_e_y)
lamb = sqrt(f_y / F_e)
P_r = phi * area * f_y * ((1 + lamb ** (2 * n)) ** (-1 / n))

calc_results = globals()
