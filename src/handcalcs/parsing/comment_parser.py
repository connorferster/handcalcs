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

    A SyntaxError or NameError propagates unchanged: it means the comment is not
    kwarg-style, and the callers fall back to the flag parser. Any other error
    comes from running the comment's code, and is raised as a
    CommentCommandError that shows that code.
    """
    stripped = strip_command_prefix(comment)
    kwarg_locals = {}
    try:
        # Positional: exec() only accepts globals/locals as keywords from Python 3.13.
        exec(stripped, {}, kwarg_locals)
    except (SyntaxError, NameError):
        raise
    except Exception as error:
        raise CommentCommandError(
            f"Error running handcalcs comment command '# {comment}': "
            f"{type(error).__name__}: {error}"
        ) from error
    return kwarg_locals
