import ast_comments as ast
import builtins
import importlib
import math
import pathlib
from dataclasses import dataclass, field
import inspect
from typing import List, Dict, Union, Any, Optional, Callable
from types import ModuleType
from collections import deque, ChainMap
from handcalcs.parsing.linetypes import (
    CalcLine,
    ExprLine,
    InlineComment,
    CommentCommand,
    CommentLine,
    MarkdownHeading,
    Attribute,
    HCNotImplemented,
    List,
    Tuple,
    Dictionary,
    String,
)
from handcalcs.parsing.blocks import (
    CalcBlock,
    FunctionBlock,
    ForBlock,
    IfBlock,
    ComprehensionBlock,
    Comprehension,
)
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
    global_exclusions: Optional[list[str]] = None
    current_line_number: int = 1
    prev_line_number: int = 0
    new_block_from_comment: bool = False
    current_block: Optional[Union[CalcBlock, FunctionBlock, ForBlock, IfBlock]] = None
    function_recurse_exclusions: list[str] = field(
        default_factory=lambda: dir(builtins)
        + dir(math)
        + ["builtins", "math", "exit", "quit"]
    )
    aliases_cache: dict = field(default_factory=dict)
    module_cache: dict = field(default_factory=dict)
    functions_cache: ChainMap = field(default_factory=ChainMap)
    ast_cache: dict = field(default_factory=dict)

    def __post_init__(self):
        # self.module_cache.update(self.globals)
        self.function_recurse_exclusions.append(f"{self.__class__.__name__}")
        if self.global_exclusions is not None:
            self.function_recurse_exclusions.extend(self.global_exclusions)
        local_callables = {}
        for name, obj in self.globals.items():
            if (
                isinstance(obj, ModuleType)
                and name not in self.function_recurse_exclusions
                and not name.startswith("__")
                and not name.startswith("@")
            ):
                source = inspect.getsource(obj)
                source_tree = ast.parse(source)
                module_callables = {}
                for node in source_tree.body:
                    if isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ):
                        module_callables[node.name] = node
                self.module_cache[name] = module_callables
                self.functions_cache = self.functions_cache.new_child(module_callables)
            elif (
                isinstance(obj, Callable)
                and name not in self.function_recurse_exclusions
                and not isinstance(obj, self.__class__)
            ):
                obj_tree = ast.parse(inspect.getsource(obj).lstrip())
                if isinstance(obj_tree, (ast.Module)):
                    obj_tree = obj_tree.body[
                        0
                    ]  # First function def within the ast.module
                local_callables.update({name: obj_tree})
                self.functions_cache = self.functions_cache.new_child(local_callables)
            else:
                self.module_cache[name] = {}
                self.functions_cache[name] = {}
        self.module_cache["__main__"] = local_callables

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
        frl = function_recurse_limit
        # --- Rule 1: Arithmetical Expressions & Parentheses (BinOp) ---
        if isinstance(node, ast.BinOp):
            add_to_current_block = True
            # A Binary Operation (e.g., a + b). The structure is:
            # [left_side, operator, right_side]
            left = self._flatten_binop(node.left, frl)
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
            val = node.id
        elif isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, str):
                val = String(value=value)
            else:
                val = value
        elif isinstance(node, ast.Compare):
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

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self.resolve_import_and_load(node)
            val = HCNotImplemented(type(node).__name__)

        elif isinstance(node, ast.Call):
            call_block = FunctionBlock()
            # Get the function name being called
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                module_name = "__main__"
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
            function_ast = None
            if func_name not in self.function_recurse_exclusions:
                function_ast = self.find_source(func_name, module_name)

            if function_ast and frl > 0:
                frl = frl - 1
                # 2. Recursively call the main conversion logic on the new source
                function_defs = self.get_function_content(function_ast, frl)
                # The result of the call node is replaced by the structure of the function's body
                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])
                function_body = dict()
                if function_defs is not None:
                    function_body = function_defs.get(func_name, dict())

                call_block.namespace = module_name
                call_block.function_name = func_name
                call_block.lines.extend(function_body.get("lines", deque()))
                call_block.params.extend(function_body.get("params", deque()))
                call_block.args.extend(args_list)
                self.current_block = call_block
            else:

                # Create the inner nested list for arguments
                args_list = deque([self.ast_parse(arg, frl) for arg in node.args])

                # Create the main nested list for the function call
                call_block.namespace = module_name
                call_block.function_name = func_name
                call_block.args.extend(args_list)

            val = call_block

        # --- Rule 3: If/Elif/Else block ---
        elif isinstance(node, ast.If):
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
            for_block = ForBlock()

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

        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            comprehension_block = ComprehensionBlock(
                type=node.__class__.__name__.replace("Comp", "").lower(),
            )

            assigns = deque([])
            keys = deque([])
            values = deque([])
            if isinstance(node, ast.DictComp):
                keys = deque([self.ast_parse(node.key, frl)])
                values = deque([self.ast_parse(node.value, frl)])
            else:
                assigns = deque([self.ast_parse(node.elt, frl)])
            comprehension_block.key = keys
            comprehension_block.value = values
            comprehension_block.assign = assigns
            generators = deque([self.ast_parse(gen, frl) for gen in node.generators])
            comp_blocks = deque([])
            for generator in generators:
                comp_block = Comprehension(
                    assigns=generator["assigns"],
                    iterator=generator["iterator"],
                    is_async=generator["is_async"],
                )
                comp_blocks.append(comp_block)
            comprehension_block.comprehensions = comp_blocks
            val = comprehension_block

            # TODO: HERE: PERHAPS I NEED SPECIAL COMPREHENSION BLOCK

        elif isinstance(node, ast.comprehension):
            comp = {
                "assigns": deque([self.ast_parse(node.target, frl)]),
                "iterator": deque([self.ast_parse(node.iter, frl)]),
                "is_async": bool(node.is_async),
            }
            val = comp

        elif isinstance(node, ast.For):
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
            expression_tree = self.ast_parse(node.value, frl)
            if not isinstance(expression_tree, deque):
                expression_tree = deque([expression_tree])
            calc_line = CalcLine(
                assigns=deque([self.ast_parse(n, frl) for n in node.targets]),
                expression_tree=expression_tree,
            )
            val = calc_line

        elif isinstance(node, ast.List):
            val = List(elems=deque([self.ast_parse(el, frl) for el in node.elts]))

        elif isinstance(node, ast.Tuple):
            val = Tuple(elems=deque([self.ast_parse(el, frl) for el in node.elts]))

        elif isinstance(node, ast.Dict):
            val = Dictionary(
                keys=deque([self.ast_parse(el, frl) for el in node.keys]),
                values=deque([self.ast_parse(el, frl) for el in node.values]),
            )

        elif isinstance(node, ast.Return):
            parsed_value = self.ast_parse(node.value, frl)
            if not isinstance(parsed_value, deque):
                parsed_value = deque([parsed_value])
            val = ExprLine(expression_tree=parsed_value, return_expr=True)

        elif isinstance(node, ast.Attribute):
            name = node.value.id
            attribute = node.attr
            val = Attribute(namespace=name, attr_name=attribute)

        elif isinstance(node, ast.Module):
            # Entry point: process all body statements
            val = deque([self.ast_parse(item, frl) for item in node.body])

        elif isinstance(node, ast.Expr):
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
            val = HCNotImplemented(node_name=type(node).__name__)

        return val

    def find_source(self, func_name: str, module_name: str) -> ast.AST:
        """Finds the source code for a function within an imported module."""

        confirmed_module_name = cmn = self.aliases_cache.get(module_name, module_name)
        confirmed_func_name = cfn = self.aliases_cache.get(func_name, func_name)
        module_definitions = self.module_cache.get(cmn, {})
        function_tree = module_definitions.get(cfn, None)
        if function_tree is None:
            function_tree = self.functions_cache.get(cfn)
        return function_tree

    def get_function_content(
        self, node: ast.FunctionDef, frl: int
    ) -> dict[str, dict[str, deque]] | None:
        """
        Returns a dictionary of functions
        """
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return {}
        else:
            acc = {}
            if isinstance(node, ast.FunctionDef):
                lines = deque([])
                for n in node.body:
                    parsed = self.ast_parse(n, frl)
                    if isinstance(parsed, ExprLine) and (  # not a docstring
                        "Doc string" in parsed.expression_tree[0]
                    ):
                        continue
                    else:

                        lines.append(parsed)
                acc.update(
                    {
                        node.name: {
                            "lines": lines,
                            "params": deque([arg.arg for arg in node.args.args]),
                        }
                    }
                )
            return acc

    def resolve_import_and_load(self, import_node: ast.Import | ast.ImportFrom):
        """Recursively resolves imported modules and loads them."""
        if isinstance(import_node, ast.Import):
            for alias in import_node.names:
                module_name = alias.name
                path = self._resolve_module_path(module_name)
                if path:
                    # Load the module, using the original name (e.g., 'my_module')
                    self.load_module_by_path(module_name, path)

    def _resolve_module_path(self, module_name: str) -> pathlib.Path | None:
        """
        Uses importlib to find the source file path for a module
        without executing any code.
        """
        try:
            # Look up the module specification
            spec = importlib.util.find_spec(module_name)
            if spec and spec.loader_state and spec.origin:
                # Return the path to the source file
                return pathlib.Path(spec.origin)
        except (ValueError, AttributeError):
            # Handle cases where the module isn't found or is a built-in
            return None
        return None

    def load_module_by_path(self, module_name: str, file_path: pathlib.Path):
        """Loads and parses a module's source code into the cache."""
        if module_name in self.module_cache:
            return
        try:
            source_code = file_path.read_text()
            module_ast: ast.Module = ast.parse(source_code, filename=str(file_path))
            self.ast_cache[module_name] = module_ast

            # Build the symbol table (namespace) for this module
            symbols = {}
            for node in module_ast.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    symbols[node.name] = node
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    self.resolve_import_and_load(node)

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # Map the local alias (or module name) to the external module name
                            local_name = alias.asname if alias.asname else alias.name
                            self.aliases_cache[local_name] = {alias.name}
                    else:
                        # ast.ImportFrom: Currently does not handle fancy . or .. style imports
                        # But this clause is where that would be implemented
                        for alias in node.names:
                            # Map the local alias (or module name) to the external module name
                            level = node.level
                            local_name = alias.asname if alias.asname else alias.name
                            self.aliases_cache[local_name] = {alias.name}

            self.module_cache[module_name] = symbols
            self.functions_cache = self.functions_cache.new_child(symbols)

        except FileNotFoundError:
            print(f"Error: Source file not found for {module_name} at {file_path}")
        except SyntaxError as e:
            print(f"Error: Syntax error in {module_name}: {e}")

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
