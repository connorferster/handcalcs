from dataclasses import dataclass
from collections import deque, ChainMap
from typing import Callable, Optional
from .ast_parser import AST_Parser
from .block_nodes import ElifBlock, IfBlock, HcBlockNode
from copy import deepcopy
from typing import Any
from .nodes import HcNode


@dataclass
class HCSequence(HcNode):
    sequence: deque
    name: str = 'root'
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

        tree = HCSequence.apply_blocks(tree, convert_if_tree)
        tree = HCSequence.set_levels(tree, level=0)
        return cls(tree, c_globals, c_locals)

    @staticmethod
    def apply_blocks(tree: deque, apply: Callable, *args, **kwargs):
        # ctree = deepcopy(tree)
        for idx, node in enumerate(tree):
            if hasattr(node, 'lines'):
                updated_node = apply(tree[idx], *args, **kwargs)
                tree[idx] = updated_node
                HCSequence.apply_blocks(node.lines, apply)
        return tree

    @staticmethod
    def set_levels(tree: deque, level: int):
        """
        Walks the tree and applies the .level attribute to each
        node according to their nesting within the tree.
        ElifBlocks do not cause an increment but their child
        IfBlocks do.
        """
        for idx, node in enumerate(tree):
            updated_node = set_level(node, level)
            if hasattr(node, 'lines') and isinstance(node, ElifBlock):
                tree[idx] = updated_node
                HCSequence.set_levels(node.lines, level)
            elif hasattr(node, 'lines') and not isinstance(node, ElifBlock):
                tree[idx] = updated_node
                HCSequence.set_levels(node.lines, level+1)  
        return tree

    @staticmethod
    def dump_tree(tree):
        """
        Walks the tree and applies the .level attribute to each
        node according to their nesting within the tree.
        ElifBlocks do not cause an increment but their child
        IfBlocks do.
        """
        acc = deque([])
        for idx, node in enumerate(tree):
            if hasattr(node, "expression_tree"):
                acc.extend(flatten_deque(node.expression_tree))
            elif hasattr(node, 'lines'):
                acc.append([str(node.__class__)])
                acc.extend(HCSequence.dump_tree(node.lines))
        return acc


def convert_if_tree(node: HcBlockNode) -> HcBlockNode:
    if isinstance(node, IfBlock):
        return ElifBlock.from_if_tree(node)
    else:
        return node

def set_level(node: HcBlockNode, level: int) -> HcBlockNode:
    node.level = level
    return node


def flatten_deque(d: deque, **config_options) -> deque:
    new_deque = deque([])
    for item in flatten(d):
        new_deque.append(item)
    return new_deque


def flatten(items: Any, omit_parentheses: bool = False) -> deque:
    """Returns elements from a deque and flattens elements from sub-deques.
    Inserts latex parentheses ( '\\left(' and '\\right)' ) where sub-deques
    used to exists, except if the reason for the sub-deque was to encapsulate
    either a fraction or an integral (then no parentheses).
    """
    if isinstance(items, deque):
        for item in items:
            yield from flatten(item)  # recursion!
    else:
        yield items