from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.parsing.sequence import HCSequence
from handcalcs.parsing.comments import is_comment_command, split_commands, is_markdown_heading
from handcalcs.parsing.blocks import (
    CalcLine,
    ExprLine,
    FunctionBlock, 
    IfBlock, 
    ForBlock,
    ElifBlock,
    ElseBlock
)

from handcalcs.parsing.datatypes import (
    HCNotImplemented,
    List,
    Name,
    NoValue
)

from handcalcs.parsing.inlines import (
    FunctionCall,
    ComprehensionChain,
    Comprehension,
)
import math
import pytest
from collections import deque

import submodule_1 as sub1
import submodule_2 as sub2

@pytest.fixture
def basic_parser():
    parser = AST_Parser(globals(), global_exclusions=['collections', 'deque'])
    return parser

def test_calc_lines(basic_parser):
    source_1 = """a = d = 4"""
    source_2 = """b = (a + b * (2 + a/4)) / (3 * a)"""
    source_3 = """c = math.sin(b / a)**2 + math.cos(b / a)**2"""

    assert basic_parser(source_1) == deque([
        CalcLine(assigns=deque([Name('a'), Name("d")]), expression_tree=deque([4]))
    ])
    assert basic_parser(source_2) == deque([
            CalcLine(
                assigns=deque([Name('b')]), 
                expression_tree=deque([
                    deque([
                        Name("a"), "+", deque([Name("b"), "*", deque([2, "+", deque([Name("a"), "/", 4])])])
                    ]),
                    "/",
                    deque([3, "*", Name("a")])
                ])
            )
    ])

    assert basic_parser(source_3) == deque([
            CalcLine(
                assigns=deque([Name("c")]), 
                expression_tree=deque([
                    deque([
                        FunctionCall(
                            namespace=deque(["math"]), 
                            function_name=deque(["sin"]), 
                            args=deque([deque([Name("b"), "/", Name("a")])]), 
                        ), "**", 2]),
                    "+",
                    deque([
                    FunctionCall(
                        namespace=deque(["math"]),
                        function_name=deque(["cos"]),
                        args=deque([deque([Name("b"), "/", Name("a")])]),
                    ), "**", 2]),
                ])
            ),
        ])


# def test_function_recursion(basic_parser):
#     source_1 = "a = sub1.my_calc(2, 3)"
#     source_2 = "b = 4; c = 5; d=6; e=3; p = sub1.my_other_calc(b, c, d, e)"
#     assert basic_parser(source_1) == deque([
#                 CalcLine(
#                     assigns=deque([Name("a")]),
#                     expression_tree=deque([
#                         FunctionBlock(
#                             namespace=deque(["sub1"]),
#                             function_name=deque(["my_calc"]),
#                             args=deque([2, 3]),
#                             params=deque([Name("q"), Name("r")]),
#                             lines=deque([
#                                 CalcLine(assigns=deque([Name("area")]), expression_tree=deque([Name("q"), "*", Name("r")])),
#                                 CalcLine(assigns=deque([Name("perimeter")]), expression_tree=deque([deque([2, "*", Name("q")]), "+", deque([2, "*", Name("r")])])),
#                                 CalcLine(assigns=deque([Name("ratio")]), expression_tree=deque([Name("area"), "/", Name("perimeter")])),
#                                 ExprLine(expression_tree=deque([Name("ratio")]), _return_expr=True)
#                             ])
#                         )
#                     ])
#                 )
#         ])
    
#     assert basic_parser(source_2) == deque([
#         CalcLine(
#             assigns=deque([Name('b', 4)]),
#             expression_tree=deque([4])
#         ),
#         CalcLine(
#             assigns=deque([Name('c', 5)]),
#             expression_tree=deque([5])
#         ),
#         CalcLine(
#             assigns=deque([Name('d', 6)]),
#             expression_tree=deque([6])
#         ),
#         CalcLine(
#             assigns=deque([Name('e', 3)]),
#             expression_tree=deque([3])
#         ),
#         CalcLine(
#             assigns=deque(['p']),
#             expression_tree=deque([
#                 FunctionBlock(
#                     namespace=deque(["sub1"]),
#                     function_name=deque(["my_other_calc"]),
#                     args=deque([Name("b", 4), Name("c", 5), Name("d", 6), Name("e", 3)]),
#                     params=deque([Name("w"), Name("y"), Name("t"), Name("s")]),
#                     lines=deque([
#                         CalcLine(
#                             assigns=deque(['factored']),
#                             expression_tree=deque([
#                                 0.9, '*', FunctionBlock(
#                                     namespace='__main__',
#                                     function_name='different_calc',
#                                     args=deque([Name('w'), Name('y'), Name('t'), Name('s')]),
#                                     params=deque([Name('s'), Name('t'), Name('u'), Name('v')]),
#                                     lines=deque([
#                                         ExprLine(
#                                             return_expr=True,
#                                             expression_tree=deque([
#                                                 deque([
#                                                     Attribute(
#                                                         namespace='math',
#                                                         attr_name='pi'
#                                                     ),
#                                                     '*', 's', '*', 't',
#                                                 ]),
#                                                 "/",
#                                                 deque([
#                                                     deque([
#                                                         'u', '*', 'v'
#                                                     ])
#                                                     , '**', 2
#                                                 ])
#                                             ])
#                                         )
#                                     ])
#                                 )
#                             ])
#                         ),
#                         ExprLine(
#                             return_expr=True,
#                             expression_tree=deque(['factored'])
#                         )
#                     ])
#                 )
#             ])
#         ),
#     ])


def test_if_blocks(basic_parser):
    source_1 = """
a = 4
b = 5
if 2 <= a < 5:
    d = 4
    print(d)
elif a > b:
    d = 5
    print(d)
else:
    d = 6
    print(d)
"""
    assert basic_parser(source_1) == deque([
        CalcLine(
            assigns=deque([Name("a")]),
            expression_tree=deque([4]),
        ),
        CalcLine(
            assigns=deque([Name("b")]),
            expression_tree=deque([5])
        ),
        IfBlock(
            test=deque([2, "<=", Name("a"), "<", 5]),
            orelse=deque([
                IfBlock(
                    test=deque([Name("a"), ">", Name("b")]),
                    orelse=deque([
                        CalcLine(
                            assigns=deque([Name("d")]),
                            expression_tree=deque([6]),
                        ),
                        ExprLine(
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(["__main__"]),
                                    function_name=deque(["print"]),
                                    args=deque([Name("d")]),
                                ),
                            ])
                        ),
                    ]),
                        
                    lines=deque([
                        CalcLine(
                            assigns=deque([Name("d")]),
                            expression_tree=deque([5])
                        ),
                        ExprLine(
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(["__main__"]),
                                    function_name=deque(["print"]),
                                    args=deque([Name("d")]),
                                )
                            ])
                        )
                    ])
                )
            ]),
            lines=deque([
                CalcLine(
                    assigns=deque([Name("d")]),
                    expression_tree=deque([4])
                ),
                ExprLine(
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(["__main__"]),
                            function_name=deque(["print"]),
                            args=deque([Name("d")]),
                        )
                    ])
                )
            ]),
        )
    ])
    
def test_for_blocks():
    source_1 = """import math
a = [0, 1, 2, 3, 4, 5]
b = 6
acc = []
for elem in a:
    value = elem + b
    acc.append(value)
"""
    source_2 = """
a = [0, 1, 2, 3, 4, 5]
b = 6
values = [elem + b for elem in a]
"""
    source_1_locals = {}
    exec(source_1, locals=source_1_locals)
    basic_parser = AST_Parser(globals() | source_1_locals, global_exclusions=['collections', 'deque'])
    assert basic_parser(source_1) == deque([
        HCNotImplemented(node_name="Import"),
        CalcLine(
            assigns=deque([Name("a", [0, 1, 2, 3, 4, 5])]),
            expression_tree=deque([
                List(
                    elems=deque([0, 1, 2, 3, 4, 5])
                )
            ])
        ),
        CalcLine(
            assigns=deque([Name("b", 6)]),
            expression_tree=deque([6]),
        ),
        CalcLine(
            assigns=deque([Name('acc', [6, 7, 8, 9, 10, 11])]),
            expression_tree=deque([List(elems=deque([]))])
        ),
        ForBlock(
            assigns=deque([Name("elem", 5)]),
            iterator=deque([Name("a", [0, 1, 2, 3, 4, 5])]),
            lines=deque([
                CalcLine(
                    assigns=deque([Name("value", 11)]),
                    expression_tree=deque([
                        Name('elem', 5), '+', Name('b', 6)
                    ])
                ),
                ExprLine(
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(["acc"]),
                            function_name=deque(["append"]),
                            args=deque([Name("value", 11)])
                        )
                    ])
                )
            ])
        )
    ])

    source_2_locals = {}
    exec(source_2, locals=source_2_locals)
    basic_parser = AST_Parser(globals() | source_2_locals, global_exclusions=['collections', 'deque'])
    assert basic_parser(source_2) == deque([
        CalcLine(
            assigns=deque([Name("a", [0, 1, 2, 3, 4, 5])]),
            expression_tree=deque([List(elems=deque([0, 1, 2, 3, 4, 5]))])
        ),
        CalcLine(
            assigns=deque([Name('b', 6)]),
            expression_tree=deque([6])
        ),
        CalcLine(
            assigns=deque([Name("values", [6, 7, 8, 9, 10, 11])]),
            expression_tree=deque([
                ComprehensionChain(
                    _type="list",
                    assign=deque([
                        deque([Name('elem'), '+', Name('b', 6)])
                    ]),
                    comprehensions=deque([
                        Comprehension(
                            assigns=deque([Name("elem")]),
                            iterator=deque([Name('a', [0, 1, 2, 3, 4, 5])]),
                            _is_async=False
                        )
                    ])
                )
            ])
        )
    ])

# # TESTS: Comments, Inline comments, comment commands
# # TODO: Implement inline comment commands? Possible? Easy?

def test_elif_block():
    ib = IfBlock(
            test=deque([2, "<=", Name("a"), "<", 5]),
            orelse=deque([
                IfBlock(
                    test=deque([Name("a"), ">", Name("b")]),
                    orelse=deque([
                        CalcLine(
                            assigns=deque([Name("d")]),
                            expression_tree=deque([6]),
                        ),
                        ExprLine(
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(["__main__"]),
                                    function_name=deque(["print"]),
                                    args=deque([Name("d")]),
                                ),
                            ])
                        ),
                    ]),
                        
                    lines=deque([
                        CalcLine(
                            assigns=deque([Name("d")]),
                            expression_tree=deque([5])
                        ),
                        ExprLine(
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(["__main__"]),
                                    function_name=deque(["print"]),
                                    args=deque([Name("d")]),
                                )
                            ])
                        )
                    ])
                )
            ]),
            lines=deque([
                CalcLine(
                    assigns=deque([Name("d")]),
                    expression_tree=deque([4])
                ),
                ExprLine(
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(["__main__"]),
                            function_name=deque(["print"]),
                            args=deque([Name("d")]),
                        )
                    ])
                )
            ]),
        )
    assert ElifBlock.from_if_tree(ib) == ElifBlock(
    lines=deque([
        IfBlock(
            lines=deque([
                CalcLine(
                    level=0,
                    assigns=deque([Name(identifier='d', value=NoValue())]),
                    expression_tree=deque([4]),
                    _numeric=deque(),
                    _result=None,
                    _comment='',
                    _latex=''
                ),
                ExprLine(
                    level=0,
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(['__main__']),
                            function_name=deque(['print']),
                            args=deque([Name(identifier='d', value=NoValue())])
                        )
                    ]),
                    _numeric=deque(),
                    _return_expr=False,
                    _result=None,
                    _comment='',
                    _latex=''
                )
            ]),
            test=deque([2, '<=', Name(identifier='a', value=NoValue()), '<', 5]),
            orelse=None
        ),
        IfBlock(
            lines=deque([
                CalcLine(
                    level=0,
                    assigns=deque([Name(identifier='d', value=NoValue())]),
                    expression_tree=deque([5]),
                    _numeric=deque(),
                    _result=None,
                    _comment='',
                    _latex=''
                ),
                ExprLine(
                    level=0,
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(['__main__']),
                            function_name=deque(['print']),
                            args=deque([Name(identifier='d', value=NoValue())])
                        )
                    ]),
                    _numeric=deque(),
                    _return_expr=False,
                    _result=None,
                    _comment='',
                    _latex=''
                )
            ]),
            test=deque([
                Name(identifier='a', value=NoValue()),
                '>',
                Name(identifier='b', value=NoValue())
            ]),
            orelse=None
        ),
        ElseBlock(
            lines=deque([
                CalcLine(
                    level=0,
                    assigns=deque([Name(identifier='d', value=NoValue())]),
                    expression_tree=deque([6]),
                    _numeric=deque(),
                    _result=None,
                    _comment='',
                    _latex=''
                ),
                ExprLine(
                    level=0,
                    expression_tree=deque([
                        FunctionCall(
                            namespace=deque(['__main__']),
                            function_name=deque(['print']),
                            args=deque([Name(identifier='d', value=NoValue())])
                        )
                    ]),
                    _numeric=deque(),
                    _return_expr=False,
                    _result=None,
                    _comment='',
                    _latex=''
                )
            ])
        )
    ])
)  


def test_hcsequence():
    source_1 = """
a = 4
b = 5
if 2 <= a < 5:
    d = 4
    if d == 3:
        print(d)
    elif d == 5:
        print(d)
    elif d == 4: 
        print(d)
    else:
        print("TWELVE")
    print(d)
elif a > b:
    d = 5
    print(d)
else:
    d = 6
    print(d)
"""
    seq = HCSequence.from_source(source_1, {"a": 4, "b": 5, "d": 4}, {})
    from rich import print
    print(seq.dump_tree(seq.sequence))
    assert False
    assert seq == HCSequence(
    sequence=deque([
        CalcLine(
            level=0,
            assigns=deque([Name(identifier='a', value=4)]),
            expression_tree=deque([4]),
            _numeric=deque(),
            _result=None,
            _comment='',
            _latex=''
        ),
        CalcLine(
            level=0,
            assigns=deque([Name(identifier='b', value=5)]),
            expression_tree=deque([5]),
            _numeric=deque(),
            _result=None,
            _comment='',
            _latex=''
        ),
        ElifBlock(
            lines=deque([
                IfBlock(
                    lines=deque([
                        CalcLine(
                            level=0,
                            assigns=deque([Name(identifier='d', value=4)]),
                            expression_tree=deque([4]),
                            _numeric=deque(),
                            _result=None,
                            _comment='',
                            _latex=''
                        ),
                        ElifBlock(
                            lines=deque([
                                IfBlock(
                                    lines=deque([
                                        ExprLine(
                                            level=0,
                                            expression_tree=deque([
                                                FunctionCall(
                                                    namespace=deque([
                                                        '__main__'
                                                    ]),
                                                    function_name=deque([
                                                        'print'
                                                    ]),
                                                    args=deque([
                                                        Name(
                                                            identifier='d',
                                                            value=4
                                                        )
                                                    ])
                                                )
                                            ]),
                                            _numeric=deque(),
                                            _return_expr=False,
                                            _result=None,
                                            _comment='',
                                            _latex=''
                                        )
                                    ]),
                                    test=deque([
                                        Name(identifier='d', value=4),
                                        '==',
                                        3
                                    ]),
                                    orelse=None
                                ),
                                IfBlock(
                                    lines=deque([
                                        ExprLine(
                                            level=0,
                                            expression_tree=deque([
                                                FunctionCall(
                                                    namespace=deque([
                                                        '__main__'
                                                    ]),
                                                    function_name=deque([
                                                        'print'
                                                    ]),
                                                    args=deque([
                                                        Name(
                                                            identifier='d',
                                                            value=4
                                                        )
                                                    ])
                                                )
                                            ]),
                                            _numeric=deque(),
                                            _return_expr=False,
                                            _result=None,
                                            _comment='',
                                            _latex=''
                                        )
                                    ]),
                                    test=deque([
                                        Name(identifier='d', value=4),
                                        '==',
                                        5
                                    ]),
                                    orelse=None
                                ),
                                IfBlock(
                                    lines=deque([
                                        ExprLine(
                                            level=0,
                                            expression_tree=deque([
                                                FunctionCall(
                                                    namespace=deque([
                                                        '__main__'
                                                    ]),
                                                    function_name=deque([
                                                        'print'
                                                    ]),
                                                    args=deque([
                                                        Name(
                                                            identifier='d',
                                                            value=4
                                                        )
                                                    ])
                                                )
                                            ]),
                                            _numeric=deque(),
                                            _return_expr=False,
                                            _result=None,
                                            _comment='',
                                            _latex=''
                                        )
                                    ]),
                                    test=deque([
                                        Name(identifier='d', value=4),
                                        '==',
                                        4
                                    ]),
                                    orelse=None
                                ),
                                ElseBlock(
                                    lines=deque([
                                        ExprLine(
                                            level=0,
                                            expression_tree=deque([
                                                FunctionCall(
                                                    namespace=deque([
                                                        '__main__'
                                                    ]),
                                                    function_name=deque([
                                                        'print'
                                                    ]),
                                                    args=deque(['TWELVE'])
                                                )
                                            ]),
                                            _numeric=deque(),
                                            _return_expr=False,
                                            _result=None,
                                            _comment='',
                                            _latex=''
                                        )
                                    ])
                                )
                            ])
                        ),
                        ExprLine(
                            level=0,
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(['__main__']),
                                    function_name=deque(['print']),
                                    args=deque([
                                        Name(identifier='d', value=4)
                                    ])
                                )
                            ]),
                            _numeric=deque(),
                            _return_expr=False,
                            _result=None,
                            _comment='',
                            _latex=''
                        )
                    ]),
                    test=deque([
                        2,
                        '<=',
                        Name(identifier='a', value=4),
                        '<',
                        5
                    ]),
                    orelse=None
                ),
                IfBlock(
                    lines=deque([
                        CalcLine(
                            level=0,
                            assigns=deque([Name(identifier='d', value=4)]),
                            expression_tree=deque([5]),
                            _numeric=deque(),
                            _result=None,
                            _comment='',
                            _latex=''
                        ),
                        ExprLine(
                            level=0,
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(['__main__']),
                                    function_name=deque(['print']),
                                    args=deque([
                                        Name(identifier='d', value=4)
                                    ])
                                )
                            ]),
                            _numeric=deque(),
                            _return_expr=False,
                            _result=None,
                            _comment='',
                            _latex=''
                        )
                    ]),
                    test=deque([
                        Name(identifier='a', value=4),
                        '>',
                        Name(identifier='b', value=5)
                    ]),
                    orelse=None
                ),
                ElseBlock(
                    lines=deque([
                        CalcLine(
                            level=0,
                            assigns=deque([Name(identifier='d', value=4)]),
                            expression_tree=deque([6]),
                            _numeric=deque(),
                            _result=None,
                            _comment='',
                            _latex=''
                        ),
                        ExprLine(
                            level=0,
                            expression_tree=deque([
                                FunctionCall(
                                    namespace=deque(['__main__']),
                                    function_name=deque(['print']),
                                    args=deque([
                                        Name(identifier='d', value=4)
                                    ])
                                )
                            ]),
                            _numeric=deque(),
                            _return_expr=False,
                            _result=None,
                            _comment='',
                            _latex=''
                        )
                    ])
                )
            ])
        )
    ]),
    c_globals={'a': 4, 'b': 5, 'd': 4},
    c_locals={}
)
