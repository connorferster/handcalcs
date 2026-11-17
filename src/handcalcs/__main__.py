"""
The command line interface: render a Python script with handcalcs.

    python -m handcalcs beam.py --renderer excel --output beam.xlsx
    python -m handcalcs beam.py -o beam.docx            # renderer from the extension
    python -m handcalcs beam.py                          # text to stdout
    python -m handcalcs beam.py -r html --theme-color "#1d4ed8" -o beam.html

Any option the CLI itself does not define is passed to the renderer as a
keyword argument (``--sheet-name Loads`` becomes ``sheet_name="Loads"``). A
value is read as a Python literal when it is one (``3``, ``True``,
``{"num_format": "0.00"}``) and as a string otherwise; an option without a
value is ``True``. The handcalcs options ``--format-code``, ``--line-values``
and ``--hidden-by-default`` set the matching ``handcalcs.set_option`` for the
run. Only the standard library is used.
"""

import argparse
import ast
import importlib
import inspect
import pathlib
import sys
from typing import Any, Optional, Sequence

from . import config
from .interfaces.object_oriented import HandCalcs
from .renderers import BaseRenderer, get_renderer
from .renderers.base import _RENDERER_REGISTRY

PROG = "handcalcs"

# The renderer an --output file's extension selects when --renderer is not given.
EXTENSION_RENDERERS = {
    ".xlsx": "excel",
    ".docx": "word",
    ".tex": "latex",
    ".md": "markdown",
    ".html": "html",
    ".htm": "html",
    ".txt": "ascii",
}

# Constructor parameters that the CLI does not offer as renderer options:
# 'filepath' is what --output does, and 'document' takes a python-docx object.
HIDDEN_PARAMETERS = frozenset({"self", "filepath", "document"})

# The handcalcs options a run may set (the renderer-selection options are
# what --renderer does).
CONFIG_OPTIONS = tuple(
    name for name in config.DEFAULTS if name not in config.RENDERER_OPTIONS
)

DESCRIPTION = "Render a Python script as handcalcs calculations."


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0
    cli_arguments, extras = split_arguments(argv, parser)
    args = parser.parse_args(cli_arguments)

    for module in args.imports:
        try:
            importlib.import_module(module)
        except ImportError as error:
            parser.error(f"could not import {module!r} ({error})")
    if args.list_renderers:
        print(renderer_listing())
        return 0
    if args.source is None:
        parser.error("the following arguments are required: source")

    options = parse_options(extras, parser)
    renderer_name = choose_renderer(args.renderer, args.output, parser)
    renderer_cls = get_renderer(renderer_name)
    if renderer_cls is None:
        parser.error(
            f"no renderer named {renderer_name!r}. Available: "
            f"{', '.join(renderer_names())}. A custom renderer's module must be "
            "imported with --import first."
        )

    settings = {name: options.pop(name) for name in CONFIG_OPTIONS if name in options}
    renderer = make_renderer(renderer_cls, options, parser)
    source = read_source(args.source, parser)

    # The handcalcs options apply to this run only, and the script's own
    # directory is importable during it (as with 'python script.py'); both are
    # undone afterwards, so main() can be called in-process.
    previous = config.get_config()
    path_entry = None
    if args.source != "-":
        path_entry = str(pathlib.Path(args.source).resolve().parent)
        sys.path.insert(0, path_entry)
    try:
        for name, value in settings.items():
            try:
                config.set_option(name, value)
            except (TypeError, ValueError) as error:
                parser.error(f"--{option_flag(name)}: {error}")
        return render(HandCalcs(renderer=renderer), source, args, parser)
    finally:
        for name in settings:
            if name in previous:
                config.set_option(name, previous[name])
            else:
                config.reset_option(name)
        if path_entry is not None and path_entry in sys.path:
            sys.path.remove(path_entry)


def render(
    hc: HandCalcs,
    source: str,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
    """Write the render to --output, or print it (text only) to stdout."""
    if args.output is not None and args.output != "-":
        path = hc(source, destination=args.output)
        if not args.quiet:
            print(f"Wrote {path}", file=sys.stderr)
        return 0
    rendered = hc(source)
    if not isinstance(rendered, str):
        parser.error(
            f"the {hc.renderer.name!r} renderer writes a file, not text; "
            "give it one with --output"
        )
    text = hc.renderer.preamble + rendered + hc.renderer.postamble
    sys.stdout.write(text if not text or text.endswith("\n") else text + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=DESCRIPTION,
        epilog=epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Renderer options are free-form, so a prefix of a CLI option (e.g.
        # --out) must not swallow one of them.
        allow_abbrev=False,
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="the Python script to render ('-' reads it from stdin)",
    )
    parser.add_argument(
        "-r",
        "--renderer",
        metavar="NAME",
        help=(
            "the renderer to use. Default: chosen from the --output extension, "
            "else the 'default_renderer' option "
            f"({config.get_option('default_renderer', 'ascii')!r})"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help=(
            "write the render to FILE (a complete document: .tex, .html, .docx, "
            ".xlsx, ...). Default: print text to stdout"
        ),
    )
    parser.add_argument(
        "--import",
        dest="imports",
        action="append",
        default=[],
        metavar="MODULE",
        help=(
            "import MODULE first, so that a custom renderer it defines can be "
            "chosen by name (repeatable)"
        ),
    )
    parser.add_argument(
        "-l",
        "--list-renderers",
        action="store_true",
        help="list the available renderers and their options, then exit",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="don't report the file written"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {package_version()}"
    )
    return parser


def epilog() -> str:
    lines = [
        "renderer options:",
        "  Any other --name VALUE is passed to the renderer as name=VALUE (dashes",
        "  become underscores). VALUE is read as a Python literal if it is one, else",
        "  as a string; --name alone is True. handcalcs options can be set the same",
        "  way: " + ", ".join(f"--{option_flag(name)}" for name in CONFIG_OPTIONS) + ".",
        "",
        renderer_listing(),
        "",
        "examples:",
        f"  {PROG} beam.py                                   print the calcs as text",
        f"  {PROG} beam.py -o beam.xlsx                      Excel, from the extension",
        f"  {PROG} beam.py -r excel -o beam.xlsx --sheet-name Beam",
        f"  {PROG} beam.py -r latex --format-code .3f > beam.tex",
        f"  {PROG} beam.py -o beam.html --theme-color '#1d4ed8'",
    ]
    return "\n".join(lines)


def renderer_names() -> list[str]:
    return sorted(name for name in _RENDERER_REGISTRY if name != "base")


def renderer_options(renderer_cls: type[BaseRenderer]) -> list[inspect.Parameter]:
    """The constructor parameters of ``renderer_cls`` offered as CLI options."""
    parameters = inspect.signature(renderer_cls.__init__).parameters.values()
    return [
        parameter
        for parameter in parameters
        if parameter.name not in HIDDEN_PARAMETERS
        and parameter.kind
        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]


def renderer_listing() -> str:
    extensions: dict[str, list[str]] = {}
    for extension, name in EXTENSION_RENDERERS.items():
        extensions.setdefault(name, []).append(extension)
    lines = ["renderers:"]
    for name in renderer_names():
        renderer_cls = _RENDERER_REGISTRY[name]
        suffix = ", ".join(extensions.get(name, []))
        lines.append(f"  {name}" + (f"  ({suffix})" if suffix else ""))
        for parameter in renderer_options(renderer_cls):
            lines.append(f"      --{option_flag(parameter.name)}{describe_default(parameter)}")
    return "\n".join(lines)


def describe_default(parameter: inspect.Parameter) -> str:
    """'  (default: ...)' for the listing; a long default shows only its type."""
    if parameter.default is inspect.Parameter.empty:
        return ""
    text = repr(parameter.default)
    if len(text) > 40:
        text = f"a {type(parameter.default).__name__}"
    return f"  (default: {text})"


def option_flag(name: str) -> str:
    return name.replace("_", "-")


def split_arguments(
    argv: list[str], parser: argparse.ArgumentParser
) -> tuple[list[str], list[tuple[str, Optional[str]]]]:
    """
    Split ``argv`` into the CLI's own arguments and the free-form options
    (``--name value``, ``--name=value`` or ``--name`` alone), wherever the
    latter appear. A free-form option takes the next argument as its value
    unless that starts with '-'. After ``--``, every argument is the CLI's.
    """
    known = {option for action in parser._actions for option in action.option_strings}
    cli_arguments: list[str] = []
    options: list[tuple[str, Optional[str]]] = []
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            cli_arguments.extend(argv[index:])
            break
        flag, has_value, value = argument.partition("=")
        if not argument.startswith("--") or flag in known:
            cli_arguments.append(argument)
        elif has_value:
            options.append((flag, value))
        elif index + 1 < len(argv) and not argv[index + 1].startswith("-"):
            options.append((flag, argv[index + 1]))
            index += 1
        else:
            options.append((flag, None))
        index += 1
    return cli_arguments, options


def parse_options(
    extras: list[tuple[str, Optional[str]]], parser: argparse.ArgumentParser
) -> dict:
    """The free-form options as keyword arguments, their values read by ``literal``."""
    options: dict[str, Any] = {}
    for flag, value in extras:
        name = flag[2:].replace("-", "_")
        if not name.isidentifier():
            parser.error(f"unrecognized argument: {flag!r}")
        options[name] = True if value is None else literal(value)
    return options


def literal(value: str) -> Any:
    """``value`` as a Python literal if it is one, else the string itself."""
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return value


def choose_renderer(
    name: Optional[str], output: Optional[str], parser: argparse.ArgumentParser
) -> str:
    if name is not None:
        return name
    if output is not None and output != "-":
        extension = pathlib.Path(output).suffix.lower()
        if extension in EXTENSION_RENDERERS:
            return EXTENSION_RENDERERS[extension]
        parser.error(
            f"can't tell the renderer from the extension of {output!r}; "
            "choose one with --renderer"
        )
    return config.get_option("default_renderer", config.DEFAULTS["default_renderer"])


def make_renderer(
    renderer_cls: type[BaseRenderer], options: dict, parser: argparse.ArgumentParser
) -> BaseRenderer:
    accepted = {parameter.name for parameter in renderer_options(renderer_cls)}
    takes_any = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in inspect.signature(renderer_cls.__init__).parameters.values()
    )
    unknown = [name for name in options if name not in accepted]
    if unknown and not takes_any:
        valid = sorted(f"--{option_flag(name)}" for name in accepted) + [
            f"--{option_flag(name)}" for name in CONFIG_OPTIONS
        ]
        parser.error(
            f"the {renderer_cls.name!r} renderer has no option "
            f"{', '.join('--' + option_flag(name) for name in unknown)}. "
            f"Its options: {', '.join(valid)}"
        )
    try:
        return renderer_cls(**options)
    except (TypeError, ValueError, FileNotFoundError) as error:
        parser.error(f"{renderer_cls.name!r} renderer: {error}")


def read_source(source: str, parser: argparse.ArgumentParser) -> str:
    if source == "-":
        return sys.stdin.read()
    path = pathlib.Path(source)
    if not path.is_file():
        parser.error(f"no such file: {source!r}")
    return path.read_text(encoding="utf-8")


def package_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("handcalcs")
    except PackageNotFoundError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
