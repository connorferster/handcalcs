from dataclasses import dataclass
from collections import deque
from handcalcs.calcline import CalcLine, IntertextLine
from typing import Union, Optional

class CalcOptions(dict):
    pass

class FunctionOptions(dict):
    pass

class ForOptions(dict):
    pass

class IfOptions(dict):
    pass

@dataclass
class HandCalcsBlock:
    options: dict

@dataclass
class ParametersBlock(HandCalcsBlock):
    lines: deque[Union[CalcLine, IntertextLine]]

@dataclass
class CalcBlock(HandCalcsBlock):
    lines: deque[Union[CalcLine, IntertextLine]]
    options: CalcOptions | dict

@dataclass
class FunctionBlock(HandCalcsBlock):
    blocks: list[HandCalcsBlock]
    options: FunctionOptions | dict

@dataclass
class ForBlock(HandCalcsBlock):
    blocks: list[HandCalcsBlock]
    options: ForOptions | dict

@dataclass
class IfBlock(HandCalcsBlock):
    blocks: list[HandCalcsBlock]
    options: IfOptions | dict