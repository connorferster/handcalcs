from collections import deque
from typing import Callable
from .blocks import HandCalcsBlock
from .linetypes import HandCalcsObj
from .renderables import HandCalcsRenderable

class BlockWalker:

    def __init__(self, blocks):
        self.blocks = blocks

    def walk_the_walk(self, hc_tree: deque, funcs: list[Callable]):
        for elem in hc_tree:
            if isinstance(elem, deque):
                self.walk_the_walk(elem, funcs)
            elif isinstance(elem, (HandCalcsBlock, HandCalcsObj)):
                self.walk(elem, funcs)
            elif isinstance(elem, HandCalcsRenderable):
                for func in funcs:
                    func(elem)
            

    def walk(self, block: HandCalcsBlock | HandCalcsObj, funcs: list[Callable]):
        """
        Walks the tree of blocks calling funcs on each deque contained
        within an attribute of each block.
        """
        for obj_name, obj in vars(block).items():
            if isinstance(obj, (HandCalcsBlock, HandCalcsObj)):
                self.walk(obj, funcs)
            elif isinstance(obj, deque):
                self.walk_the_walk(obj, funcs)
            elif not obj_name.startswith("_"):
                for func in funcs:
                    func(obj)


