"""A value with a tolerance that writes its own LaTeX, like an uncertainty package's."""


class Tolerance:
    def __init__(self, nom, tol):
        self.nom, self.tol = nom, tol

    def __mul__(self, other):
        return Tolerance(self.nom * other, self.tol * other)

    __rmul__ = __mul__

    def __format__(self, spec):
        return f"{self.nom:g} ± {self.tol:g}"

    def _repr_latex_(self):
        return f"${self.nom:g} \\pm {self.tol:g}$"
