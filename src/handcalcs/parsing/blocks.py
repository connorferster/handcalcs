from dataclasses import dataclass, field
from collections import deque
from handcalcs.parsing.linetypes import CalcLine, MarkdownHeading, ExprLine
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
    lines: deque[Union[CalcLine, ExprLine]] = field(default_factory=deque)


@dataclass
class CalcBlock(HandCalcsBlock):
    lines: deque[Union[CalcLine, ExprLine]] = field(default_factory=deque)
    options: Optional[CalcOptions | dict] = field(default_factory=dict)


@dataclass
class FunctionBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock] = field(default_factory=deque)
    options: FunctionOptions | dict = field(default_factory=dict)
    module_name: str = ""
    function_name: str = ""
    args: deque[str] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)


@dataclass
class ForBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock] = field(default_factory=deque)
    options: Optional[ForOptions | dict] = field(default_factory=dict)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[str] = field(default_factory=deque)


@dataclass
class IfBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock] = field(default_factory=deque)
    options: Optional[IfOptions | dict] = field(default_factory=dict)
    test: deque[HandCalcsBlock] = field(default_factory=deque)
    orelse: deque[HandCalcsBlock] = field(default_factory=deque)


@dataclass
class MarkupBlock(HandCalcsBlock):
    lines: deque[MarkdownHeading] = field(default_factory=deque)
    options: dict = field(default_factory=dict)
