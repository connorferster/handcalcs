"""
Taken from latexify_py by Yusuke Oda
"""

import ast
from typing import Union
from .. import helpers


class DocstringRemover(ast.NodeTransformer):
    """NodeTransformer to remove all docstrings.

    Docstrings here are detected as Expr nodes with a single string constant.
    """

    def visit_Expr(self, node: ast.Expr) -> Union[ast.Expr, None]:
        if helpers.is_str(node.value):
            return None
        return node