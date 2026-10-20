import argparse


class CommentCommandError(ValueError):
    """A ``# hc:`` comment command that cannot be parsed."""


class CommentCommandParser(argparse.ArgumentParser):
    """
    An ArgumentParser for ``# hc:`` comments. argparse's ``error()`` prints a
    usage message and calls ``sys.exit(2)``, which would end the user's whole
    program over a typo in a comment; this one raises instead.
    """

    def error(self, message: str):
        raise CommentCommandError(message)


# add_help=False frees ``-h`` for the params-block command (this parser reads
# ``# hc:`` comments, never a real command line).
command_parser = CommentCommandParser(prog="# hc:", add_help=False)


class JoinWords(argparse.Action):
    """Store a multi-word value as one space-separated string (``--mode no_num no_sym``)."""

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, " ".join(values))


command_parser.add_argument("-m", "--multiline", "--mult", action="store_true")
command_parser.add_argument("-f", "--format-code")
command_parser.add_argument("-w", "--if-winner-only", "--winner", action="store_false")
command_parser.add_argument("-i", "--ignore", action="store_true")
command_parser.add_argument("-p", "--param-line", action="store_true")
command_parser.add_argument("-b", "--line-break", action="store_true")
# A page break before the next line (standalone) or after this one (inline).
command_parser.add_argument(
    "--pagebreak", "--page-break", dest="page_break", action="store_true"
)
command_parser.add_argument("-c", "--param-cols", "--param_cols", type=int)
# The calc-line columns to show; see ``mode_columns`` in renderers/base.py
# (e.g. ``--mode no_num``, ``--mode ass sym res``). ``-m`` is ``--multiline``.
command_parser.add_argument("--mode", nargs="+", action=JoinWords)

command_parser.add_argument("-h", "--params-block", "--params", action="store_true")


def parse_commands(comment: str, args: list[str]) -> dict:
    """
    Parse the flags of the ``# hc:`` comment ``comment`` (already split into
    ``args``). Raises CommentCommandError naming the comment if they are invalid.
    """
    try:
        return vars(command_parser.parse_args(args))
    except CommentCommandError as error:
        raise CommentCommandError(
            f"Invalid handcalcs comment command '# {comment}': {error}"
        ) from None
