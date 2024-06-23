import ast
from typing import Any

def is_number(s: str) -> bool:
    """
    A basic helper function because Python str methods do not
    have this ability...
    """
    try:
        float(s)
        return True
    except:
        return False
    

def dict_get(d: dict, item: Any) -> Any:
    """
    Return the item from the dict, 'd'.
    """
    try:
        return d.get(item, item)
    except TypeError:
        return item


## The following functions shamelessly stolen from https://github.com/google/latexify_py

def make_name(id: str) -> ast.Name:
    """Generates a new Name node.

    Args:
        id: Name of the node.

    Returns:
        Generated ast.Name.
    """
    return ast.Name(id=id, ctx=ast.Load())


def make_attribute(value: ast.expr, attr: str):
    """Generates a new Attribute node.

    Args:
        value: Parent value.
        attr: Attribute name.

    Returns:
        Generated ast.Attribute.
    """
    return ast.Attribute(value=value, attr=attr, ctx=ast.Load())


def make_constant(value: Any) -> ast.expr:
    """Generates a new Constant node.

    Args:
        value: Value of the node.

    Returns:
        Generated ast.Constant or its equivalent.

    Raises:
        ValueError: Unsupported value type.
    """
    if (
        value is None
        or value is ...
        or isinstance(value, (bool, int, float, complex, str, bytes))
    ):
        return ast.Constant(value=value)

    raise ValueError(f"Unsupported type to generate Constant: {type(value).__name__}")


def is_constant(node: ast.AST) -> bool:
    """Checks if the node is a constant.

    Args:
        node: The node to examine.

    Returns:
        True if the node is a constant, False otherwise.
    """
    return isinstance(node, ast.Constant)


def is_str(node: ast.AST) -> bool:
    """Checks if the node is a str constant.

    Args:
        node: The node to examine.

    Returns:
        True if the node is a str constant, False otherwise.
    """
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def extract_int_or_none(node: ast.expr) -> int | None:
    """Extracts int constant from the given Constant node.

    Args:
        node: ast.Constant or its equivalent representing an int value.

    Returns:
        Extracted int value, or None if extraction failed.
    """
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.n, bool)
    ):
        return node.value


    return None


def extract_int(node: ast.expr) -> int:
    """Extracts int constant from the given Constant node.

    Args:
        node: ast.Constant or its equivalent representing an int value.

    Returns:
        Extracted int value.

    Raises:
        ValueError: Not a subtree containing an int value.
    """
    value = extract_int_or_none(node)

    if value is None:
        raise ValueError(f"Unsupported node to extract int: {type(node).__name__}")

    return value


def extract_function_name_or_none(node: ast.Call) -> str | None:
    """Extracts function name from the given Call node.

    Args:
        node: ast.Call.

    Returns:
        Extracted function name, or None if not found.
    """
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None
