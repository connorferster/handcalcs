import ast_comments as ast
import builtins
import math
from dataclasses import dataclass, field
import inspect
from typing import List, Dict, Union, Any, Optional
from collections import deque
from handcalcs.parsing.linetypes import (
    CalcLine,
    ExprLine,
    InlineComment,
    CommentCommand,
    CommentLine,
    MarkdownHeading,
    Attribute,
    HCNotImplemented,
)
from handcalcs.parsing.blocks import CalcBlock, FunctionBlock, ForBlock, IfBlock
from handcalcs.parsing.commands import command_parser
import handcalcs.parsing.comments as comments

ARITHMETIC_OPS = {
    "Add": "+",
    "Sub": "-",
    "Mult": "*",
    "Div": "/",
    "Floor": "//",
    "Pow": "**",
    "Mod": "%",
}

COMPARE_OPS = {
    "Eq": "==",
    "Ne": "!=",
    "GtE": ">=",
    "Gt": ">",
    "LtE": "<=",
    "Lt": "<",
}


# HERE: ast_parse to parse block comments, block options, and blocks in order to val = a "hc_tree"
@dataclass
class AST_Parser:
    globals: dict = field(default_factory=dict)
    current_line_number: int = 1
    prev_line_number: int = 0
    new_block_from_comment: bool = False
    current_block: Optional[Union[CalcBlock, FunctionBlock, ForBlock, IfBlock]] = None
    function_recurse_exclusions: list[str] = field(
        default_factory=lambda: dir(builtins) + dir(math)
    )

    def __call__(self, source: str, function_recurse_limit: int = 3) -> deque:
        """
        Returns the handcalcs tree from the source.
        """
        ast_tree = ast.parse(source)
        hc_tree = self.ast_parse(ast_tree, function_recurse_limit)
        self.clear()
        return hc_tree
    
    def clear(self):
        """
        Clears existing data out of the parser.
        """
        self.current_block = None
        self.current_line_number = 1
        self.prev_line_number = 0
        self.new_block_from_comment = False

    def ast_parse(self, node: ast.AST, function_recurse_limit: int) -> deque:
        """
        Recursively converts an AST node into the custom nested list/dict structure.
        """
        new_line = True
        if hasattr(node, "lineno"):
            self.current_line_number = node.lineno
        else:
            self.current_line_number = 0
        if self.current_line_number == self.prev_line_number:
            new_line = False
        # print(f"Start: {self.current_block=}")
        frl = function_recurse_limit
        # --- Rule 1: Arithmetical Expressions & Parentheses (BinOp) ---
        if isinstance(node, ast.BinOp):
            # print("BinOp")
            add_to_current_block = True
            # A Binary Operation (e.g., a + b). The structure is:
            # [left_side, operator, right_side]
            left = self._flatten_binop(node.left, frl)
            # print(f"{left=}")
            op_name = type(node.op).__name__
            op = ARITHMETIC_OPS.get(
                op_name, op_name
            )  # Get the operator name (e.g., 'Add', 'Mult')

            right = self.ast_parse(node.right, frl)
            # When an expression inside parentheses is encountered, it is an expression
            # itself that will be processed recursively. For example, in (a + b) * c,
            # the (a + b) is the 'left' part of the outer BinOp, and its result
            # 'a + b' will be a nested list: ['a', 'Add', 'b'].

            # To strictly satisfy the 'whenever parentheses are included' rule,
            # we check if the sub-expression was an ast.Subscript or an ast.Call
            # as these often imply an operation that was enclosed. However, in AST,
            # explicit parentheses *do not* create a separate node unless they're
            # used for grouping in an expression, which results in recursive BinOps.
            # The recursive call `self.ast_parse` naturally handles the nesting.

            val = deque([left, op, right])

        # --- Rule 1: Simplest case (e.g., variable names, constants) ---
        elif isinstance(node, ast.Name):
            # print("Name")
            val = node.id
        elif isinstance(node, ast.Constant):
            # print("Constant")
            val = node.value
        elif isinstance(node, ast.Compare):
            # print("Compare")
            # Comparison operations (e.g., a > b). Structure:
            # [left, op_name, right] (simplified for this structure)
            left = self.ast_parse(node.left, frl)
            op_names = [type(op).__name__ for op in node.ops]
            comparator_names = [self.ast_parse(n, frl) for n in node.comparators]
            ops = [COMPARE_OPS.get(op_name, op_name) for op_name in op_names]
            matched = list(zip(ops, comparator_names))
            val = deque([])
            val.append(left)
            for pair in matched:
                val.append(pair[0])
                val.append(pair[1])

        elif isinstance(node, ast.Call):
            # print("Call")
            call_block = FunctionBlock()
            # print(f"HERE: {call_block=}")
            # Get the function name being called
            if isinstance(node.func, ast.Name):
                print("First")
                func_name = node.func.id
                module_name = ""
            elif isinstance(node.func, ast.Attribute):
                print("Second")
                # Example: module.external_func
                func_name = node.func.attr
                print(f"{func_name=}")
                module_name = (
                    node.func.value.id
                )  # Assumes the module name is the attribute's value
            else:
                print("Third")
                # Complex call, e.g., a function returned by another function
                # Fall back to standard Rule 2
                # ... (original Rule 2 logic) ...
                module_name = ""
                func_name = self.ast_parse(
                    node.func, frl
                )  # Get the function's name (str)
                if isinstance(func_name, ast.Attribute):
                    module_name = func_name.module_name
                    func_name = func_name.attr_name

                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])

                # Create the main nested list for the function call
                val = deque([func_name, deque([args_list])])

            # # Check for a specific target function you want to recurse into
            # if func_name == "external_func" and module_name == "some_module":

            # 1. Get the source code string for the external function
            external_source = None
            if func_name not in self.function_recurse_exclusions:
                external_source = self.find_source(func_name, module_name)
            print(f"{external_source=}")

            if external_source and frl > 0:
                print("Primero")
                frl = frl - 1
                # 2. Recursively call the main conversion logic on the new source
                external_ast = ast.parse(external_source)
                function_defs = self.collect_function_defs(external_ast, frl)
                # The result of the call node is replaced by the structure of the function's body
                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])
                function_body = dict()
                if function_defs is not None:
                    function_body = function_defs.get(func_name, dict())

                call_block.module_name = module_name
                call_block.function_name = func_name
                call_block.lines.extend(function_body.get("lines", deque()))
                call_block.params.extend(function_body.get("params", deque()))
                call_block.args.extend(args_list)
                self.current_block = call_block
            else:
                print("Segundo") # Get the function's name (str)

                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])

                # Create the main nested list for the function call
                call_block.module_name = module_name
                call_block.function_name = func_name
                call_block.args.extend(args_list)

            val = call_block

        # --- Rule 3: If/Elif/Else block ---
        elif isinstance(node, ast.If):
            # print("If")
            if_block = IfBlock()

            # "test": The condition (nested list via recursive call)
            if_block.test = self.ast_parse(node.test, frl)

            # "body": The block of code inside the if (nested list of statements)
            if_block.lines.extend(
                deque([self.ast_parse(item, frl) for item in node.body])
            )

            # "orelse": The block of code inside the else/elif (nested list)
            if node.orelse:
                # If `orelse` contains another `ast.If` (an `elif`), we recursively
                # call self.ast_parse on that one.
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    if_block.orelse = deque([self.ast_parse(node.orelse[0], frl)])
                else:
                    # Standard `else` block or multiple statements in `orelse`
                    if_block.orelse = deque(
                        [self.ast_parse(item, frl) for item in node.orelse]
                    )
            else:
                if_block.orelse = deque()  # Empty list for no `else`

            val = self.current_block = if_block

        # --- Rule 4: For loop block ---
        elif isinstance(node, ast.For):
            # print("For")
            for_block = ForBlock()
            # A dictionary is created within the list
            for_dict: Dict[str, Any] = {}

            # "target": str of the assigned target
            # Assumes the target is a simple variable name (ast.Name)
            if isinstance(node.target, ast.Name):
                for_block.assigns.append(node.target.id)
            else:
                print(f"ForBlock, alternate target: {node.target=}")

            # "body": nested list of the for loop's body
            for_block.lines.extend(
                deque([self.ast_parse(item, frl) for item in node.body])
            )

            # "iter": str showing the name of the iteration variable
            # Assumes the iterator is a simple variable name (ast.Name)
            # Note: Iterators can be more complex (like function calls or lists)
            # We'll simplify to just the source code if it's not a simple Name.
            if isinstance(node.iter, ast.Name):
                for_block.iterator = deque([node.iter.id])
            else:
                # If it's a more complex expression, we'll try to convert it
                # into a string representation for simplicity in this rule.
                for_block.iterator = self.ast_parse(node.iter, frl)

            val = self.current_block = for_block

        elif isinstance(node, ast.Comment):
            print(f"{node.value=} | {node.inline=}")
            if not new_line:
                val = InlineComment(comment=node.value)
            else:
                comment_value = node.value
                if comments.is_markdown_heading(comment_value):
                    val = MarkdownHeading(comment=comment_value)
                elif comments.is_comment_command(comment_value):
                    split_commands = comments.split_commands(comment_value)
                    parsed_commands = vars(command_parser.parse_args(split_commands))
                    val = CommentCommand(
                        raw_commands=comment_value, parsed_commands=parsed_commands
                    )
                else:
                    val = CommentLine(comment=comment_value)

        # --- Other important nodes (e.g., Assignments, List construction) ---
        elif isinstance(node, ast.Assign):
            # print("Assign")
            expression_tree = self.ast_parse(node.value, frl)
            if not isinstance(expression_tree, deque):
                expression_tree = deque([expression_tree])
            calc_line = CalcLine(
                assigns=deque([self.ast_parse(n, frl) for n in node.targets]),
                expression_tree=expression_tree,
            )
            val = calc_line
            


        elif isinstance(node, ast.List):
            # print("List")
            # Lists: ['List', [item1, item2, ...]]
            val = deque(["array", deque([self.ast_parse(el, frl) for el in node.elts])])

        elif isinstance(node, ast.Return):
            # print("Return")
            parsed_value = self.ast_parse(node.value, frl)
            if not isinstance(parsed_value, deque):
                parsed_value = deque([parsed_value])
            val = ExprLine(
                expression_tree=parsed_value, return_expr=True
            )

        elif isinstance(node, ast.Attribute):
            # print("Attribute")
            name = node.value.id
            attribute = node.attr
            val = Attribute(module_name=name, attr_name=attribute)

        elif isinstance(node, ast.Module):
            # print("Module")
            # Entry point: process all body statements
            val = deque([self.ast_parse(item, frl) for item in node.body])

        elif isinstance(node, ast.Expr):
            # print("Expr")
            # An expression used as a statement (e.g., a standalone function call)
            if isinstance(node.value, ast.Constant):
                doc_string = f"Doc string: {self.ast_parse(node.value, frl)}"
                val = ExprLine(expression_tree=deque([doc_string]))
            else:
                parsed_node = self.ast_parse(node.value, frl)
                if not isinstance(parsed_node, deque):
                    parsed_node = deque([parsed_node])
                val = ExprLine(expression_tree=parsed_node)

        # Default case for unhandled nodes: val = a simple string for clarity
        else:
            # print("Unhandled")
            val = HCNotImplemented(node_name=type(node).__name__)

        return val

    def find_source(self, func_name: str, module_name: str) -> str:
        """Finds the source code for a function within an imported module."""

        # Import the module dynamically
        module = None
        if module_name:  # Might need to access globals here too
            try:
                module = __import__(module_name)
            except (ModuleNotFoundError, ImportError):
                module = self.globals.get(module_name)

        # Get the function object
        if module is not None:
            func_obj = getattr(module, func_name)

            # Get the source code as a string
            source_code = inspect.getsource(func_obj)
            return source_code
        else:
            print(
                f"Warning: Could not get source for {module_name}.{func_name}."
            )
            return ""


    def collect_function_defs(
        self, node: ast.FunctionDef, frl: int
    ) -> dict[str, dict[str, deque]] | None:
        """
        Returns a dictionary of functions
        """
        acc = {}
        for block in node.body:
            if isinstance(block, ast.FunctionDef):
                lines = deque([])
                for n in block.body:
                    parsed = self.ast_parse(n, frl)
                    if isinstance(parsed, ExprLine) and (  # not a docstring
                        "Doc string" in parsed.expression_tree[0]
                    ):
                        continue
                    else:

                        lines.append(parsed)
                acc.update(
                    {
                        block.name: {
                            "lines": lines,
                            "params": deque([arg.arg for arg in block.args.args]),
                        }
                    }
                )
        return acc

    def _flatten_binop(self, node, frl) -> deque:
        """
        Recursively flattens an ast.BinOp node into a list of operands and operators.

        The structure will be: [operand, operator, operand, operator, operand, ...]
        """
        if not isinstance(node, ast.BinOp):
            # Base case: The node is a simple operand (e.g., Name, Constant, Call, etc.)
            return self.ast_parse(node, frl)

        left_side = self._flatten_binop(node.left, frl)
        if not isinstance(left_side, deque):
            left_side = deque([left_side])
        op_name = node.op.__class__.__name__
        op = ARITHMETIC_OPS.get(op_name, op_name)
        right_side = self.ast_parse(node.right, frl)
        result = left_side + deque([op, right_side])
        return result

    # def convert_source_to_custom_list(
    #     self, source_code: str, function_recurse_limit: int = 3
    # ) -> CustomStructure:
    #     """rrfeget
    #     Parses the source code and initiates the recursive conversion.
    #     """
    #     # 1. Parse the source code into an AST
    #     tree = ast.parse(source_code)

    #     # 2. Start the recursive conversion from the root (ast.Module)
    #     val = ast_parse(tree, function_recurse_limit)
