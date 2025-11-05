import ast_comments as ast
import inspect
from typing import List, Dict, Union, Any
from collections import deque

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


# HERE: ast_parse to parse block comments, block options, and blocks in order to return a "hc_tree"

def ast_parse(node: ast.AST, function_recurse_limit: int) -> Any:
    """
    Recursively converts an AST node into the custom nested list/dict structure.
    """
    frl = function_recurse_limit
    # --- Rule 1: Arithmetical Expressions & Parentheses (BinOp) ---
    if isinstance(node, ast.BinOp):
        # A Binary Operation (e.g., a + b). The structure is:
        # [left_side, operator, right_side]
        left = ast_parse(node.left, frl)
        op_name = type(node.op).__name__
        op = ARITHMETIC_OPS.get(
            op_name, op_name
        )  # Get the operator name (e.g., 'Add', 'Mult')

        right = ast_parse(node.right, frl)
        # When an expression inside parentheses is encountered, it is an expression
        # itself that will be processed recursively. For example, in (a + b) * c,
        # the (a + b) is the 'left' part of the outer BinOp, and its result
        # 'a + b' will be a nested list: ['a', 'Add', 'b'].

        # To strictly satisfy the 'whenever parentheses are included' rule,
        # we check if the sub-expression was an ast.Subscript or an ast.Call
        # as these often imply an operation that was enclosed. However, in AST,
        # explicit parentheses *do not* create a separate node unless they're
        # used for grouping in an expression, which results in recursive BinOps.
        # The recursive call `ast_parse` naturally handles the nesting.

        return deque([left, op, right])

    # --- Rule 1: Simplest case (e.g., variable names, constants) ---
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Compare):
        # Comparison operations (e.g., a > b). Structure:
        # [left, op_name, right] (simplified for this structure)
        left = ast_parse(node.left, frl)
        op_name = type(node.ops[0]).__name__  # Assuming one operator for simplicity
        op = COMPARE_OPS.get(op_name, op_name)
        right = ast_parse(node.comparators[0], frl)
        return deque([left, op, right])
    # elif isinstance(node, ast.Call):
    #     # --- Rule 2: Function Call ---
    #     # Structure: [function_name, [list_of_arguments]]
    #     func_name = ast_parse(node.func) # Get the function's name (str)

    #     # Create the inner nested list for arguments
    #     args_list = deque([ast_parse(arg) for arg in node.args])

    #     # Create the main nested list for the function call
    #     return deque([func_name, deque([args_list])])
    elif isinstance(node, ast.Call):
        # Get the function name being called
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            module_name = "current_file"  # You'd need a more complex way to track this

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
            func_name = ast_parse(
                node.func, frl
            )  # Get the function's name (str)

            # Create the inner nested list for arguments
            args_list = deque([ast_parse(arg, frl) for arg in node.args])

            # Create the main nested list for the function call
            return deque([func_name, deque([args_list])])

        # # Check for a specific target function you want to recurse into
        # if func_name == "external_func" and module_name == "some_module":

        # 1. Get the source code string for the external function
        external_source = find_source(func_name, module_name)
        if external_source and frl > 0:
            frl = frl - 1
            # 2. Recursively call the main conversion logic on the new source
            external_ast = ast.parse(external_source)
            function_defs = collect_function_defs(external_ast, frl)
            # The result of the call node is replaced by the structure of the function's body
            # Create the inner nested list for arguments
            args_list = deque([ast_parse(arg, frl) for arg in node.args])

            return {
                "function_name": func_name,
                "module": module_name,
                "body": function_defs.get(func_name, external_ast),
                "args": args_list,
            }
        else:
            func_name = ast_parse(
                node.func, frl
            )  # Get the function's name (str)

            # Create the inner nested list for arguments
            args_list = deque([ast_parse(arg, frl) for arg in node.args])

            # Create the main nested list for the function call
            return deque([func_name, deque([args_list])])

    # --- Rule 3: If/Elif/Else block ---
    elif isinstance(node, ast.If):
        # A dictionary is created within the list
        if_dict: Dict[str, Any] = {}

        # "test": The condition (nested list via recursive call)
        if_dict["test"] = ast_parse(node.test, frl)

        # "body": The block of code inside the if (nested list of statements)
        if_dict["body"] = [ast_parse(item, frl) for item in node.body]

        # "orelse": The block of code inside the else/elif (nested list)
        if node.orelse:
            # If `orelse` contains another `ast.If` (an `elif`), we recursively
            # call ast_parse on that one.
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                if_dict["orelse"] = ast_parse(node.orelse[0], frl)
            else:
                # Standard `else` block or multiple statements in `orelse`
                if_dict["orelse"] = [
                    ast_parse(item, frl) for item in node.orelse
                ]
        else:
            if_dict["orelse"] = []  # Empty list for no `else`

        return if_dict

    # --- Rule 4: For loop block ---
    elif isinstance(node, ast.For):
        # A dictionary is created within the list
        for_dict: Dict[str, Any] = {}

        # "target": str of the assigned target
        # Assumes the target is a simple variable name (ast.Name)
        for_dict["target"] = node.target.id

        # "body": nested list of the for loop's body
        for_dict["body"] = [ast_parse(item, frl) for item in node.body]

        # "iter": str showing the name of the iteration variable
        # Assumes the iterator is a simple variable name (ast.Name)
        # Note: Iterators can be more complex (like function calls or lists)
        # We'll simplify to just the source code if it's not a simple Name.
        if isinstance(node.iter, ast.Name):
            for_dict["iter"] = node.iter.id
        else:
            # If it's a more complex expression, we'll try to convert it
            # into a string representation for simplicity in this rule.
            for_dict["iter"] = ast_parse(node.iter, frl)

        return for_dict

    # --- Other important nodes (e.g., Assignments, List construction) ---
    elif isinstance(node, ast.Assign):
        # Assignments: [target, 'Assign', value]
        # Assumes a single target
        target = ast_parse(node.targets[0], frl)
        value = ast_parse(node.value, frl)
        return deque([target, "=", value])

    elif isinstance(node, ast.List):
        # Lists: ['List', [item1, item2, ...]]
        return deque(["array", [ast_parse(el, frl) for el in node.elts]])

    elif isinstance(node, ast.Return):
        return ast_parse(node.value, frl)

    elif isinstance(node, ast.Attribute):
        name = node.value.id
        attribute = node.attr
        return {"name": name, "attr": attribute}

    elif isinstance(node, ast.Module):
        # Entry point: process all body statements
        return deque([ast_parse(item, frl) for item in node.body])

    elif isinstance(node, ast.Expr):
        # An expression used as a statement (e.g., a standalone function call)
        return {"expr": ast_parse(node.value, frl)}

    # Default case for unhandled nodes: return a simple string for clarity
    return f"UnhandledNode: {type(node).__name__}"


def convert_source_to_custom_list(
    source_code: str, function_recurse_limit: int = 3
) -> CustomStructure:
    """
    Parses the source code and initiates the recursive conversion.
    """
    # 1. Parse the source code into an AST
    tree = ast.parse(source_code)

    # 2. Start the recursive conversion from the root (ast.Module)
    return ast_parse(tree, function_recurse_limit)


def find_source(func_name: str, module_name: str) -> str:
    """Finds the source code for a function within an imported module."""
    try:
        # Import the module dynamically
        module = __import__(module_name)

        # Get the function object
        func_obj = getattr(module, func_name)

        # Get the source code as a string
        source_code = inspect.getsource(func_obj)
        return source_code

    except (ImportError, AttributeError, OSError) as e:
        # Handle cases where the module/function isn't found or source is unavailable
        print(
            f"Warning: Could not get source for {module_name}.{func_name}. Error: {e}"
        )
        return ""


def collect_function_defs(node: ast.AST, frl: int) -> dict[str, ast.FunctionDef]:
    """
    Returns a dictionary of functions
    """
    acc = {}
    for block in node.body:
        if isinstance(block, ast.FunctionDef):
            acc.update(
                {
                    block.name: {
                        "source": deque(
                            [ast_parse(n, frl) for n in block.body]
                        ),
                        "params": deque([arg.arg for arg in block.args.args]),
                    }
                }
            )
    return acc
