from typing import Union
from ..parsing.blocks import HandCalcsBlock
from ..parsing.linetypes import HandCalcsObj


def flatten_deque(d: deque, **config_options) -> deque:
    new_deque = deque([])
    for item in flatten(d):
        new_deque.append(item)
    return new_deque


def flatten(item: Union[HandCalcsBlock, HandCalcsObj], omit_parentheses: bool = False):
    """
    """
    if isinstance(item, (HandCalcsBlock, HandCalcsObj)):
        for elem in item:
            yield from flatten(item)  # recursion!
    else:
        yield item