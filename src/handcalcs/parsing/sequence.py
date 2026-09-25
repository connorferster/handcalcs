from dataclasses import dataclass
from collections import deque, ChainMap
from typing import Callable, Optional
from .ast_parser import AST_Parser
from .block_nodes import ElifBlock, IfBlock, HcBlockNode, ParamsBlock, CommentsBlock, CalcsBlock
from copy import deepcopy
from typing import Any
from .nodes import HcNode


@dataclass
class HcSequence(HcNode):
    sequence: deque
    type: str = 'root'
    hc_globals: Optional[dict] = None
    hc_locals: Optional[dict] = None

    @classmethod
    def from_source(cls, source_code: str, hc_globals: dict, hc_locals: dict):
        """
        Builds an HcSequence tree from Python source code.
        """
        context = ChainMap(hc_locals, hc_globals)
        parser = AST_Parser(context)
        tree = parser(source_code)

        tree = HcSequence.apply_blocks(tree, convert_if_tree)
        tree = group_lines(tree)
        tree = HcSequence.set_levels(tree, level=0)
        return cls(tree, 'root', hc_globals, hc_locals)

    @staticmethod
    def apply_blocks(tree: deque, apply: Callable, *args, **kwargs):
        # ctree = deepcopy(tree)
        for idx, node in enumerate(tree):
            if hasattr(node, 'lines'):
                updated_node = apply(tree[idx], *args, **kwargs)
                tree[idx] = updated_node
                HcSequence.apply_blocks(node.lines, apply)
        return tree

    @staticmethod
    def set_levels(tree: deque, level: int):
        """
        Walks the tree and applies the .level attribute to each
        node according to their nesting within the tree.
        ElifBlocks do not cause an increment but their child
        IfBlocks do.
        """
        # ElifBlock and ParamsBlock are not nested scopes: their child lines
        # render at the same level as the block itself, so they do not increment
        # the indent level for their children.
        flat_blocks = (ElifBlock, ParamsBlock, CommentsBlock, CalcsBlock)
        for idx, node in enumerate(tree):
            if hasattr(node, 'level'): # Omit NoValue nodes
                updated_node = set_level(node, level)
            if hasattr(node, 'lines') and isinstance(node, flat_blocks):
                tree[idx] = updated_node
                HcSequence.set_levels(node.lines, level)
            elif hasattr(node, 'lines') and not isinstance(node, flat_blocks):
                tree[idx] = updated_node
                HcSequence.set_levels(node.lines, level+1)
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
                acc.extend(HcSequence.dump_tree(node.lines))
        return acc


# Blocks whose children are already a single logical group: grouping must not
# descend into them (that would re-group already-grouped lines) nor treat them
# as loose lines to be gathered.
_ALREADY_GROUPED = (ParamsBlock, CommentsBlock, CalcsBlock)


def _group_kind(node: HcNode) -> Optional[str]:
    """
    Classify a node by the run it may join, or None if it is a run boundary.

    Consecutive nodes sharing a kind are gathered into one block; anything
    returning None (headings, commands, imports, nested blocks) breaks a run.
    """
    node_type = getattr(node, 'type', None)
    if node_type == 'comment_line':
        return 'comments'
    if node_type in ('calc_line', 'expr_line'):
        return 'calcs'
    return None


def group_lines(tree: deque) -> deque:
    """
    Gather maximal runs of consecutive comment lines into a CommentsBlock and
    consecutive calc/expr lines into a CalcsBlock, in a single forward pass.

    The accumulator ('run') is the lookahead: each node either extends the
    current run, or flushes it and starts a new one/passes through as a run
    boundary. Nested scopes (if/for/function/elif branches) are grouped
    recursively; blocks that are already a single group are left untouched.
    """
    grouped: deque = deque([])
    run: deque = deque([])
    run_kind: Optional[str] = None

    def flush():
        nonlocal run, run_kind
        if run:
            block_cls = CommentsBlock if run_kind == 'comments' else CalcsBlock
            grouped.append(block_cls(lines=run))
            run = deque([])
            run_kind = None

    for node in tree:
        # Recurse into nested scopes so their bodies are grouped too, but never
        # into blocks that are themselves already a single group.
        if hasattr(node, 'lines') and not isinstance(node, _ALREADY_GROUPED):
            node.lines = group_lines(node.lines)

        kind = _group_kind(node)
        if kind is None:
            flush()
            grouped.append(node)
        else:
            if kind != run_kind:
                flush()
            run.append(node)
            run_kind = kind
    flush()
    return grouped


def convert_if_tree(node: HcBlockNode) -> HcBlockNode:
    if isinstance(node, IfBlock):
        elif_block = ElifBlock.from_if_tree(node)
        return elif_block
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