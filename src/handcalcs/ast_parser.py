import ast_comments as ast
import builtins
import math
from dataclasses import dataclass, field
import inspect
from typing import List, Dict, Union, Any, Optional
from collections import deque
from handcalcs.calcline import CalcLine, ExprLine, IntertextLine, Attribute
from handcalcs.blocks import CalcBlock, FunctionBlock, ForBlock, IfBlock, ParametersBlock


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
    "Ge": ">=",
    "Gt": ">",
    "Le": "<=",
    "Lt": "<",
}


# HERE: ast_parse to parse block comments, block options, and blocks in order to val = a "hc_tree"
@dataclass
class AST_Parser:
    current_line_number: int = 1
    prev_line_number: int = 0
    new_block_from_comment: bool = False
    globals: dict = field(default_factory=dict)
    current_block: Optional[str] = None
    hc_tree: deque = field(default_factory=deque)
    function_recurse_exclusions: list[str] = field(default_factory=lambda: dir(builtins) + dir(math))

    

    def ast_parse(self, node: ast.AST, function_recurse_limit: int) -> Any:
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
        add_to_current_block = False
        print(f"Start: {self.current_block=}")
        frl = function_recurse_limit
        # --- Rule 1: Arithmetical Expressions & Parentheses (BinOp) ---
        if isinstance(node, ast.BinOp):
            print("BinOp")
            add_to_current_block = True
            # A Binary Operation (e.g., a + b). The structure is:
            # [left_side, operator, right_side]
            left = self.ast_parse(node.left, frl)
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
            print("Name")
            add_to_current_block = True
            val = node.id
        elif isinstance(node, ast.Constant):
            print("Constant")
            add_to_current_block = True
            val = node.value
        elif isinstance(node, ast.Compare):
            print("Compare")
            add_to_current_block = True
            # Comparison operations (e.g., a > b). Structure:
            # [left, op_name, right] (simplified for this structure)
            left = self.ast_parse(node.left, frl)
            op_name = type(node.ops[0]).__name__  # Assuming one operator for simplicity
            op = COMPARE_OPS.get(op_name, op_name)
            right = self.ast_parse(node.comparators[0], frl)
            val = deque([left, op, right])
        elif isinstance(node, ast.Call):
            print("Call")
            self.current_block = FunctionBlock()
            print(f"HERE: {self.current_block=}")
            # Get the function name being called
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                module_name = ""
            elif isinstance(node.func, ast.Attribute):
                # Example: module.external_func
                func_name = node.func.attr
                module_name = (
                    node.func.value.id
                )  # Assumes the module name is the attribute's value
            else:
                # Complex call, e.g., a function returned by another function
                # Fall back to standard Rule 2
                # ... (original Rule 2 logic) ...
                module_name = ""
                func_name = self.ast_parse(
                    node.func, frl
                )  # Get the function's name (str)

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

            if external_source and frl > 0:
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

                self.current_block.module_name = module_name
                self.current_block.function_name = func_name
                self.current_block.lines.extend(function_body.get('lines', deque()))
                self.current_block.params.extend(function_body.get('params', deque()))
                self.current_block.args.extend(args_list)
            else:
                func_name = self.ast_parse(
                    node.func, frl
                )  # Get the function's name (str)

                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])

                # Create the main nested list for the function call
                self.current_block.module_name = module_name
                self.current_block.function_name = func_name
                self.current_block.args.extend(args_list)

        # --- Rule 3: If/Elif/Else block ---
        elif isinstance(node, ast.If):
            print("If")
            self.current_block = IfBlock()

            # "test": The condition (nested list via recursive call)
            self.current_block.test = self.ast_parse(node.test, frl)

            # "body": The block of code inside the if (nested list of statements)
            self.current_block.lines.extend(
                deque([self.ast_parse(item, frl) for item in node.body])
            )

            # "orelse": The block of code inside the else/elif (nested list)
            if node.orelse:
                # If `orelse` contains another `ast.If` (an `elif`), we recursively
                # call self.ast_parse on that one.
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    self.current_block.orelse = deque([self.ast_parse(node.orelse[0], frl)])
                else:
                    # Standard `else` block or multiple statements in `orelse`
                    self.current_block.orelse = deque([
                        self.ast_parse(item, frl) for item in node.orelse
                    ])
            else:
                self.current_block.orelse = deque()  # Empty list for no `else`

        # --- Rule 4: For loop block ---
        elif isinstance(node, ast.For):
            print("For")
            self.current_block = ForBlock()
            # A dictionary is created within the list
            for_dict: Dict[str, Any] = {}

            # "target": str of the assigned target
            # Assumes the target is a simple variable name (ast.Name)
            if isinstance(node.target, ast.Name):
                self.current_block.assigns.append(node.target.id)
            else:
                print(f"ForBlock, alternate target: {node.target=}")

            # "body": nested list of the for loop's body
            self.current_block.lines.extend(
                deque([self.ast_parse(item, frl) for item in node.body])
            )

            # "iter": str showing the name of the iteration variable
            # Assumes the iterator is a simple variable name (ast.Name)
            # Note: Iterators can be more complex (like function calls or lists)
            # We'll simplify to just the source code if it's not a simple Name.
            if isinstance(node.iter, ast.Name):
                self.current_block.iterator = deque([node.iter.id])
            else:
                # If it's a more complex expression, we'll try to convert it
                # into a string representation for simplicity in this rule.
                self.current_block.iterator = self.ast_parse(node.iter, frl)

        # --- Other important nodes (e.g., Assignments, List construction) ---
        elif isinstance(node, ast.Assign):
            print("Assign")
            if not isinstance(self.current_block, CalcBlock):
                self.current_block = CalcBlock()
            # Assignments: [target, 'Assign', value]
            calc_line = CalcLine(
                assigns = deque([self.ast_parse(n, frl) for n in node.targets]),
                expression_tree=self.ast_parse(node.value, frl),
            )
            val = calc_line

        elif isinstance(node, ast.List):
            print("List")
            add_to_current_block = True
            # Lists: ['List', [item1, item2, ...]]
            val = deque(["array", deque([self.ast_parse(el, frl) for el in node.elts])])

        elif isinstance(node, ast.Return):
            print("Return")
            add_to_current_block = True
            val = self.ast_parse(node.value, frl)

        elif isinstance(node, ast.Attribute):
            print("Attribute")
            add_to_current_block = True
            name = node.value.id
            attribute = node.attr
            val = Attribute(module_name=name, attr_name=attribute)

        elif isinstance(node, ast.Module):
            print("Module")
            # Entry point: process all body statements
            val = deque([self.ast_parse(item, frl) for item in node.body])

        elif isinstance(node, ast.Expr):
            print("Expr")
            add_to_current_block = True
            # An expression used as a statement (e.g., a standalone function call)
            val = ExprLine(
                expression_tree=self.ast_parse(node.value, frl)
            )

        # Default case for unhandled nodes: val = a simple string for clarity
        else:
            print("Unhandled")
            add_to_current_block = True
            val = f"UnhandledNode: {type(node).__name__}"

        if add_to_current_block:
            if new_line:
                self.current_block.lines.append(val)
            else:
                self.current_block.lines.extend(val)
                
        return self.current_block


    def find_source(self, func_name: str, module_name: str) -> str:
        """Finds the source code for a function within an imported module."""
        try:
            # Import the module dynamically
            if module_name: # Might need to access globals here too
                module = __import__(module_name)
            else:
                module = self.globals

            # Get the function object
            if module_name:
                func_obj = getattr(module, func_name)
            else:
                func_obj = module.get(func_name)

            # Get the source code as a string
            source_code = inspect.getsource(func_obj)
            val = source_code

        except (ImportError, AttributeError, OSError, ValueError) as e:
            # Handle cases where the module/function isn't found or source is unavailable
            print(
                f"Warning: Could not get source for {module_name}.{func_name}. Error: {e}"
            )
            val = ""


    def collect_function_defs(self, node: ast.FunctionDef, frl: int) -> dict[str, dict[str, deque]] | None:
        """
        Returns a dictionary of functions
        """
        acc = {}
        for block in node.body:
            if isinstance(block, ast.FunctionDef):
                acc.update(
                    {
                        block.name: {
                            "lines": deque(
                                [self.ast_parse(n, frl) for n in block.body]
                            ),
                            "params": deque([arg.arg for arg in block.args.args]),
                        }
                    }
                )
        return acc


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
