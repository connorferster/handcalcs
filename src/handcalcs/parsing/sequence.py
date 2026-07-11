from dataclasses import dataclass
from collections import deque, ChainMap
from typing import Callable, Optional
from .ast_parser import AST_Parser
from .blocks import ElifBlock, IfBlock, HandCalcsBlock
from copy import deepcopy


@dataclass
class HCSequence:
    sequence: deque
    c_globals: Optional[dict] = None
    c_locals: Optional[dict] = None

    @classmethod
    def from_source(cls, source_code: str, c_globals: dict, c_locals: dict):
        """
        Builds an HCSequence tree from Python source code.
        """
        context = ChainMap(c_locals, c_globals)
        parser = AST_Parser(context)
        tree = parser(source_code)

        tree = HCSequence.traverse_tree_lines(tree, convert_if_tree)
        tree = HCSequence.set_levels(tree, level=0)
        return cls(tree, c_globals, c_locals)

    @staticmethod
    def traverse_tree_lines(tree: deque, apply: Callable, *args, **kwargs):
        # ctree = deepcopy(tree)
        for idx, node in enumerate(tree):
            if hasattr(node, 'lines'):
                updated_node = apply(tree[idx], *args, **kwargs)
                tree[idx] = updated_node
                HCSequence.traverse_tree_lines(node.lines, apply)
        return tree

    @staticmethod
    def set_levels(tree: deque, level: int):
        from rich import print
        # print(f"{level=}")
        # ctree = deepcopy(tree)
        for idx, node in enumerate(tree):
            updated_node = set_level(node, level)
            if hasattr(node, 'lines') and isinstance(node, ElifBlock):
                tree[idx] = updated_node
                # print(f"{updated_node=}")
                HCSequence.set_levels(node.lines, level)
            elif hasattr(node, 'lines') and not isinstance(node, ElifBlock):
                tree[idx] = updated_node
                # print(f"{updated_node=}")
                HCSequence.set_levels(node.lines, level+1)  
        return tree


def convert_if_tree(node: HandCalcsBlock) -> HandCalcsBlock:
    if isinstance(node, IfBlock):
        return ElifBlock.from_if_tree(node)
    else:
        return node

def set_level(node: HandCalcsBlock, level: int) -> HandCalcsBlock:
    node.level = level
    return node