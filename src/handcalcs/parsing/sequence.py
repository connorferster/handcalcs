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

        tree = traverse_tree_lines(tree, convert_if_tree)
        return cls(tree, c_globals, c_locals)
        
        # # Process IfBlocks into a flattened ElifBlock
        # for idx, top_node in enumerate(tree):
        #     if isinstance(top_node, IfBlock):
        #         elif_block = ElifBlock.from_if_tree(top_node)
        #         tree[idx] = elif_block




def traverse_tree_lines(tree: deque, apply: Callable):
    # ctree = deepcopy(tree)
    for idx, node in enumerate(tree):
        if hasattr(node, 'lines'):
            updated_node = apply(tree[idx])
            tree[idx] = updated_node
            traverse_tree_lines(node.lines, apply)
    return tree
        
def convert_if_tree(node: HandCalcsBlock) -> HandCalcsBlock:
    if isinstance(node, IfBlock):
        return ElifBlock.from_if_tree(node)
    else:
        return node

