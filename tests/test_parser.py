from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.parsing.comments import is_comment_command, split_commands, is_markdown_heading
from handcalcs.parsing.linetypes import CalcLine, ExprLine
from handcalcs.parsing.blocks import CalcBlock, FunctionBlock
import math
import pytest
from collections import deque

import submodule_1 as sub1
import submodule_2 as sub2

@pytest.fixture
def basic_parser():
    parser = AST_Parser(globals())
    return parser

def test_calc_lines(basic_parser):
    source_1 = """a = 4"""
    source_2 = """b = (a + b * (2 + a/4)) / (3 * a)"""
    source_3 = """c = math.sin(b / a)**2 + math.cos(b / a)**2"""

    assert basic_parser(source_1) == deque([
        CalcLine(assigns=deque(["a"]), expression_tree=deque([4]))
    ])
    assert basic_parser(source_2) == deque([
            CalcLine(
                assigns=deque(["b"]), 
                expression_tree=deque([
                    deque([
                        "a", "+", deque(["b", "*", deque([2, "+", deque(["a", "/", 4])])])
                    ]),
                    "/",
                    deque([3, "*", "a"])
                ])
            )
    ])

    assert basic_parser(source_3) == deque([
            CalcLine(
                assigns=deque(["c"]), 
                expression_tree=deque([
                    deque([
                        FunctionBlock(
                            module_name="math", 
                            function_name="sin", 
                            args=deque([deque(["b", "/", "a"])]), 
                            params=deque([])
                        ), "**", 2]),
                    "+",
                    deque([
                    FunctionBlock(
                        module_name="math",
                        function_name="cos",
                        args=deque([deque(["b", "/", "a"])]),
                        params=deque([]),
                    ), "**", 2]),
                ])
            ),
        ])


def test_function_recursion(basic_parser):
    source_1 = "a = sub1.my_calc(2, 3)"
    source_2 = "b = 4; c = 5; d=6; e=3; p = sub1.my_other_calc(b, c, d, e)"
    assert basic_parser(source_1) == deque([
                CalcLine(
                    assigns=deque(["a"]),
                    expression_tree=deque([
                        FunctionBlock(
                            module_name="sub1",
                            function_name="my_calc",
                            args=deque([2, 3]),
                            params=deque(["q", "r"]),
                            lines=deque([
                                CalcLine(assigns=deque(["area"]), expression_tree=deque(["q", "*", "r"])),
                                CalcLine(assigns=deque(["perimeter"]), expression_tree=deque([deque([2, "*", "q"]), "+", deque([2, "*", "r"])])),
                                CalcLine(assigns=deque(["ratio"]), expression_tree=deque(["area", "/", "perimeter"])),
                                ExprLine(expression_tree=deque(["ratio"]), return_expr=True)
                            ])
                        )
                    ])
                )
        ])


