class HandCalcsRenderable:
    pass

class HCString(HandCalcsRenderable, str):
    pass

class HCInt(HandCalcsRenderable, int):
    pass

class HCFloat(HandCalcsRenderable, float):
    pass

class HCComplex(HandCalcsRenderable, complex):
    pass



def parse_renderable(constant: str | int | float | complex):
    if isinstance(constant, str):
        return HCString(constant)
    elif isinstance(constant, int):
        return HCInt(constant)
    elif isinstance(constant, float):
        return HCFloat(constant)
    elif isinstance(constant, complex):
        return HCComplex(constant)