from math import sin, atan

mu = 0.44
CritSeg = 1.5  # sendo extramemente
Delta_h = 9.641
Raio = (200 / 2)  # Config
Raio_Minimo = CritSeg * Delta_h / (sin(atan(mu + 1) + 1)) ** 2

calc_results = globals()
