from submodule_2 import different_calc

def my_calc(q: float, r: float) -> float:
    area = q * r
    perimeter = 2 * q + 2 * r
    ratio = area / perimeter
    return ratio

def my_other_calc(w: float, y: float, t: float, s: float) -> float:
    factored = 0.9 * different_calc(w, y, t, s)
    return factored

