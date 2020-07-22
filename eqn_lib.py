from handcalcs.decorator import handcalc

@handcalc(jupyter_display = True)
def NBCC2015LC(DL: float = 0, SDL: float = 0, SL: float = 0, LL: float = 0, WL: float= 0, EL: float = 0):
    LC1 = 1.4*DL
    LC2a = 1.25*DL + 1.5*LL
    LC2b = 1.25*DL + 1.5*LL + 0.5*SL
    LC3a = 1.25*DL + 1.5*SL
    LC3b = 1.25*DL + 1.5*SL + 0.5*LL
    return locals()