import re
import ast


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
    For kwarg comment commands.
    """
    stripped = strip_command_prefix(comment)
    kwarg_locals = {}
    exec(stripped, locals=kwarg_locals)
    return kwarg_locals