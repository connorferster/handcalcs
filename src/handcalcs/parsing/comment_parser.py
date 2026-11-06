import re
import ast

from .commands import CommentCommandError


def is_markdown_heading(comment: str) -> bool:
    """
    Returns True if the comment represents a markdown heading.
    """
    is_markdown = False
    if comment.startswith("##"):  # Or any other number of octothorpes
        is_markdown = True
    return is_markdown


def is_comment_command(comment: str) -> bool:
    """
    Returns True if the comment represents a markdown heading.
    """
    pattern = re.compile(r"^hc\:[\s]*")
    match = pattern.match(comment)
    return bool(match)


def split_commands(comment: str) -> list[str]:
    """
    Splits the commands by white space.
    """
    commands = strip_command_prefix(comment)
    return commands.split()


def strip_command_prefix(comment: str) -> str:
    """
    Splits the commands by white space.
    """
    pattern = re.compile(r"^hc\:[\s]*")
    stripped = pattern.sub("", comment)
    return stripped


def parse_kwargs(comment: str) -> dict:
    """
    For kwarg comment commands (``# hc: mode = "ass sym"``).

    The comment is parsed, never run: it must be one or more ``name = <literal>``
    assignments (``;``-separated), and anything else raises a SyntaxError, which
    tells the callers to read it with the flag parser instead. (Running it would
    let a flag pass as an expression: ``-s`` is a valid expression once
    forallpeople's ``top_level=True`` has put ``s`` in ``builtins``.) A value that
    is not a literal (``format_code = fc``) raises a CommentCommandError.
    """
    stripped = strip_command_prefix(comment)
    tree = ast.parse(stripped)
    if not tree.body or not all(
        isinstance(stmt, ast.Assign)
        and all(isinstance(target, ast.Name) for target in stmt.targets)
        for stmt in tree.body
    ):
        raise SyntaxError(f"'{stripped}' is not a kwarg comment command")
    kwargs = {}
    for stmt in tree.body:
        try:
            value = ast.literal_eval(stmt.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            names = ", ".join(f"'{target.id}'" for target in stmt.targets)
            raise CommentCommandError(
                f"Invalid handcalcs comment command '# {comment}': the value of "
                f"{names} must be a literal (a number, string, True/False or None), "
                f"not '{ast.unparse(stmt.value)}'."
            ) from None
        for target in stmt.targets:
            kwargs[target.id] = value
    return kwargs
