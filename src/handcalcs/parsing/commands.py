import argparse
import re


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


# add_help=False frees ``-h``, the rc1 spelling of the params-block command (this parser reads
# ``# hc:`` comments, never a real command line). Every flag defaults to None, "not
# given": a command only changes the settings it names, so ``# hc: -f .2f`` leaves an
# earlier ``# hc: -m`` (or ``-i``) in effect.
command_parser = CommentCommandParser(prog="# hc:", add_help=False)


class JoinWords(argparse.Action):
    """Store a multi-word value as one space-separated string (``--mode no_num no_sym``)."""

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, " ".join(values))


command_parser.add_argument(
    "-m", "--multiline", "--mult", action="store_true", default=None
)
command_parser.add_argument("-f", "--format-code")
command_parser.add_argument(
    "-w", "--if-winner-only", "--winner", action="store_false", default=None
)
# Hide (``-i``) or show (``-s``) what follows (standalone) or this line (inline). Either
# may end with a condition, ``# hc: -s M_f > 0``; see ``split_condition``.
command_parser.add_argument("-i", "--ignore", action="store_const", const=True)
command_parser.add_argument(
    "-s", "--show", dest="ignore", action="store_const", const=False
)
command_parser.add_argument("-p", "--param-line", action="store_true", default=None)
# Show a boolean result as a pass/fail mark (#251): ``ok = DoU <= 1  # hc: --check``.
command_parser.add_argument("--check", action="store_true", default=None)
command_parser.add_argument("-b", "--line-break", action="store_true", default=None)
# A page break before the next line (standalone) or after this one (inline).
command_parser.add_argument(
    "--pagebreak", "--page-break", dest="page_break", action="store_true", default=None
)
command_parser.add_argument("-c", "--param-cols", "--param_cols", type=int)
# The calc-line columns to show; see ``mode_columns`` in renderers/base.py
# (e.g. ``--mode no_num``, ``--mode ass sym res``). ``-m`` is ``--multiline``.
command_parser.add_argument("--mode", nargs="+", action=JoinWords)

# ``-g`` (grid) opens a params block; ``-h`` is its rc1 spelling, still accepted.
command_parser.add_argument(
    "-g",
    "--grid",
    "--params-block",
    "--params",
    "-h",
    dest="params_block",
    action="store_true",
    default=None,
)


# A show/hide flag followed by an expression (not by another flag): the expression
# runs to the end of the comment.
CONDITION = re.compile(r"(?:^|\s)(-i|--ignore|-s|--show)\s+(?!-[A-Za-z-])(\S.*)$")


def split_condition(args: list[str]) -> tuple[list[str], str | None]:
    """
    The flags of ``args`` and the condition of a conditional show/hide flag
    (``-i A_s < A_req``), or None. The condition is the rest of the comment, so
    it is kept as written rather than parsed as flags (``-s M_f > -5`` would
    otherwise read ``-5`` as one).
    """
    match = CONDITION.search(" ".join(args))
    if match is None:
        return args, None
    flags = " ".join(args)[: match.start(2)].split()
    return flags, match.group(2).strip()


def parse_commands(comment: str, args: list[str]) -> dict:
    """
    Parse the flags of the ``# hc:`` comment ``comment`` (already split into
    ``args``). Raises CommentCommandError naming the comment if they are invalid.

    A conditional show/hide flag adds its expression as ``condition``; the parser
    evaluates it and replaces it with the outcome (see ``resolve_condition``).
    """
    flags, condition = split_condition(args)
    try:
        commands = vars(command_parser.parse_args(flags))
    except CommentCommandError as error:
        raise CommentCommandError(
            f"Invalid handcalcs comment command '# {comment}': {error}"
        ) from None
    if condition is not None:
        commands["condition"] = condition
    return commands


def resolve_condition(commands: dict, evaluate) -> dict:
    """
    ``commands`` with its ``condition`` replaced by the outcome: ``-i <expr>``
    hides when the expression is true and shows when it is false, ``-s <expr>``
    the reverse. ``evaluate`` returns the value of the expression.
    """
    condition = commands.pop("condition", None)
    if condition is None:
        return commands
    commands["ignore"] = commands["ignore"] == bool(evaluate(condition))
    return commands
