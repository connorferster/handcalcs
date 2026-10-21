"""
The values of a source's variables statement by statement, recorded while it runs.

handcalcs runs the source once and shows the values the variables had. Taken
from the namespace after the whole source ran, a name assigned more than once
would show its final value on every line, and an ``if`` test would be evaluated
with values from after its branch ran. ``LineValues`` instead records, while the
source runs, the values just before and just after each statement (for a
statement in a loop, during the last pass that ran it). The parser reads each
line's values from there (see ``AST_Parser``).

The recording watches the lines of the source's own frames run (with
``sys.monitoring``, or ``sys.settrace`` before Python 3.12): a new line marks the
end of one statement and the start of the next. Only the names those two
statements use are recorded, and values are not copied: an object that is
changed in place later (``xs.append(4)``) shows its final state.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from contextlib import contextmanager
from dataclasses import dataclass
from types import FrameType
from typing import Callable, Iterator, Optional

# Compound statements and the part of each that is its header line(s).
HEADER_END = {
    ast.If: lambda node: node.test,
    ast.While: lambda node: node.test,
    ast.For: lambda node: node.iter,
    ast.AsyncFor: lambda node: node.iter,
}

# The parts of a compound statement whose names it uses itself (its body's
# statements record their own).
HEADER_PARTS = {
    ast.If: ("test",),
    ast.While: ("test",),
    ast.For: ("target", "iter"),
    ast.AsyncFor: ("target", "iter"),
    ast.With: ("items",),
    ast.AsyncWith: ("items",),
}

# ``{{ ... }}`` in a comment, and the names in it.
JINJA_EXPRESSION = re.compile(r"{{(.*?)}}")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(slots=True)
class StatementValues:
    """
    The values of the names one statement uses, just ``before`` and just
    ``after`` it ran (for a statement in a loop, in the last pass). None when
    the statement did not run.
    """

    before: Optional[dict] = None
    after: Optional[dict] = None


class LineValues:
    """
    The values each statement of ``source`` ran with: ``statements`` maps the
    first line of each statement to its ``StatementValues``. ``line_offset`` is
    added to the source's line numbers to give the line numbers of the running
    code (for a function body taken from its file).
    """

    def __init__(self, source: str, line_offset: int = 0):
        tree = ast.parse(source)
        self.line_offset = line_offset
        # The names the source assigns. Only these can change while it runs, so
        # only these are recorded: any other name has the same value on every
        # line as after the run.
        self.names = assigned_names(tree)
        # The line of the running code -> the first line (in 'source') of the
        # innermost statement on it.
        self.statement_of_line: dict[int, int] = {}
        # The first line of each statement -> the names it uses.
        self.statement_names: dict[int, frozenset] = {}
        self.loop_headers: set[int] = set()
        self._map_statements(tree.body)
        # Names in ``{{ }}`` in comments are recorded with every statement.
        self.comment_names = comment_names(source) & self.names
        self.statements: dict[int, StatementValues] = {}

    def values_before(self, line: int) -> Optional[dict]:
        """The values just before the statement starting on ``line`` ran."""
        values = self.statements.get(line)
        return values.before if values is not None else None

    def values_after(self, line: int) -> Optional[dict]:
        """The values just after the statement starting on ``line`` ran."""
        values = self.statements.get(line)
        return values.after if values is not None else None

    def _map_statements(self, body: list) -> None:
        for stmt in body:
            # A compound statement owns its header lines only; its body's lines
            # belong to the statements in it.
            header = HEADER_END.get(type(stmt))
            if header is not None:
                last = header(stmt).end_lineno
            elif hasattr(stmt, "body"):
                last = stmt.lineno
            else:
                last = stmt.end_lineno
            if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                self.loop_headers.add(stmt.lineno)
            for line in range(stmt.lineno, last + 1):
                self.statement_of_line.setdefault(line + self.line_offset, stmt.lineno)
            self.statement_names[stmt.lineno] = self.statement_names.get(
                stmt.lineno, frozenset()
            ) | (used_names(stmt) & self.names)
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(stmt, field, None)
                if isinstance(inner, list) and inner and isinstance(inner[0], ast.stmt):
                    self._map_statements(inner)
            for handler in getattr(stmt, "handlers", []):
                self._map_statements(handler.body)

    def recorder(self) -> tuple[Callable, Callable]:
        """
        The functions a recording calls, which run for every line of the source
        (so they keep their state in local variables):

        - ``on_line(code, line, frame=None)`` for a line event: a
          ``sys.monitoring`` LINE callback as it is, or called with the frame
          for a ``sys.settrace`` line event;
        - ``finish(frame)``, when a recorded frame returns.
        """
        statement_of_line = self.statement_of_line
        statement_names = self.statement_names
        comment_names = self.comment_names
        statements = self.statements
        loop_headers = self.loop_headers
        # The names recorded when one statement ends and the next starts: the
        # names of both (one snapshot is the end of one and the start of the other).
        transition_names: dict[tuple, tuple] = {}
        current = [None]

        def on_line(code, line: int, frame: Optional[FrameType] = None) -> None:
            statement = statement_of_line.get(line)
            previous = current[0]
            if statement is None or statement == previous:
                # A line within the statement that is running records nothing.
                return
            if frame is None:
                # Called by sys.monitoring, from the source's frame.
                frame = sys._getframe(1)
            key = (previous, statement)
            names = transition_names.get(key)
            if names is None:
                names = statement_names[statement] | comment_names
                if previous is not None:
                    names |= statement_names[previous]
                names = transition_names[key] = tuple(names)
            f_locals = frame.f_locals
            snapshot = {name: f_locals[name] for name in names if name in f_locals}
            if len(snapshot) < len(names):
                # In a function, a name may be global; or it is not assigned yet.
                snapshot = snapshot_of(frame, names)
            if previous is not None:
                statements[previous].after = snapshot
            values = statements.get(statement)
            if values is None:
                statements[statement] = StatementValues(before=snapshot)
            elif statement not in loop_headers:
                # A loop's header runs again on every pass; it keeps the values
                # it started with.
                values.before = snapshot
            current[0] = statement

        def finish(frame: FrameType) -> None:
            previous = current[0]
            if previous is not None:
                names = statement_names[previous] | comment_names
                statements[previous].after = snapshot_of(frame, names)
            current[0] = None

        return on_line, finish


def assigned_names(tree: ast.Module) -> frozenset:
    """
    The names ``tree`` assigns anywhere: assignment, loop and ``with`` targets,
    imports, ``def`` and ``class`` names. After ``from module import *``, every
    name it uses may be assigned.
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    return frozenset(
                        n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
                    )
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
    return frozenset(names)


def used_names(stmt: ast.stmt) -> frozenset:
    """The names a statement uses itself (a compound statement, in its header)."""
    parts = HEADER_PARTS.get(type(stmt))
    if parts is None:
        if hasattr(stmt, "body"):
            return frozenset()
        nodes = [stmt]
    else:
        nodes = []
        for part in parts:
            value = getattr(stmt, part)
            nodes.extend(value if isinstance(value, list) else [value])
    return frozenset(
        node.id
        for root in nodes
        for node in ast.walk(root)
        if isinstance(node, ast.Name)
    )


def comment_names(source: str) -> set:
    """The identifiers inside ``{{ }}`` in the source's comments."""
    if "{{" not in source:
        return set()
    names = set()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for token in tokens:
        if token.type == tokenize.COMMENT:
            for expression in JINJA_EXPRESSION.findall(token.string):
                names.update(IDENTIFIER.findall(expression))
    return names


def snapshot_of(frame: FrameType, names: tuple) -> dict:
    """The values of ``names`` in ``frame`` (a name not defined there is left out)."""
    f_locals = frame.f_locals
    snapshot = {name: f_locals[name] for name in names if name in f_locals}
    if len(snapshot) < len(names):
        # A function's frame: its globals (and a module's builtins) are elsewhere.
        f_globals = frame.f_globals
        for name in names:
            if name not in snapshot and name in f_globals:
                snapshot[name] = f_globals[name]
    return snapshot


@contextmanager
def recording(
    values: LineValues, accept: Callable[[FrameType], bool]
) -> Iterator[LineValues]:
    """
    Record ``values`` while the block runs, from the frames ``accept`` picks
    (the frames that run the source).

    On Python 3.12+ this uses ``sys.monitoring``, which reports the lines of the
    accepted code only, so the libraries the source calls run at full speed.
    Otherwise (or if no monitoring tool id is free) it uses ``sys.settrace``,
    and restores a trace function set before (a debugger's) afterwards.
    """
    monitoring = getattr(sys, "monitoring", None)
    tool = _free_tool_id(monitoring) if monitoring is not None else None
    if tool is None:
        with _settrace_recording(values, accept):
            yield values
    else:
        with _monitoring_recording(values, accept, monitoring, tool):
            yield values


def _free_tool_id(monitoring) -> Optional[int]:
    # Ids 3 and 4 are not assigned to a kind of tool; 2 (profiler) and 5
    # (optimizer) are tried when they are taken.
    for tool in (3, 4, 2, 5):
        if monitoring.get_tool(tool) is None:
            return tool
    return None


@contextmanager
def _monitoring_recording(values, accept, monitoring, tool: int):
    events = monitoring.events
    traced = []

    def on_start(code, offset):
        frame = sys._getframe(1)
        if accept(frame):
            monitoring.set_local_events(tool, code, events.LINE | events.PY_RETURN)
            traced.append(code)
            return None
        # Not the source: this code is not reported again.
        return monitoring.DISABLE

    on_line, finish = values.recorder()

    def on_return(code, offset, retval):
        finish(sys._getframe(1))

    monitoring.use_tool_id(tool, "handcalcs")
    # Code that an earlier recording left out may be the source this time.
    monitoring.restart_events()
    monitoring.register_callback(tool, events.PY_START, on_start)
    monitoring.register_callback(tool, events.LINE, on_line)
    monitoring.register_callback(tool, events.PY_RETURN, on_return)
    monitoring.set_events(tool, events.PY_START)
    try:
        yield
    finally:
        monitoring.set_events(tool, 0)
        for code in traced:
            monitoring.set_local_events(tool, code, 0)
        for event in (events.PY_START, events.LINE, events.PY_RETURN):
            monitoring.register_callback(tool, event, None)
        monitoring.free_tool_id(tool)


@contextmanager
def _settrace_recording(values, accept):
    on_line, finish = values.recorder()

    def trace_lines(frame: FrameType, event: str, arg) -> Callable:
        if event == "line":
            on_line(frame.f_code, frame.f_lineno, frame)
        elif event == "return":
            finish(frame)
        return trace_lines

    def trace_calls(frame: FrameType, event: str, arg) -> Optional[Callable]:
        if event == "call" and accept(frame):
            return trace_lines
        return None

    previous = sys.gettrace()
    sys.settrace(trace_calls)
    try:
        yield
    finally:
        sys.settrace(previous)


def run(source: str, namespace: dict, filename: str = "<handcalcs>") -> LineValues:
    """Run ``source`` in ``namespace``, recording its values line by line."""
    values = LineValues(source)
    code = compile(source, filename, "exec")
    with recording(values, lambda frame: frame.f_code is code):
        exec(code, namespace)
    return values
