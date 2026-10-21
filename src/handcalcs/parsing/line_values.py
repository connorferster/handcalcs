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
end of one statement and the start of the next. Only the names
the source refers to are recorded, and values are not copied: an object that is
changed in place later (``xs.append(4)``) shows its final state.
"""

from __future__ import annotations

import ast
import sys
from contextlib import contextmanager
from types import FrameType
from typing import Callable, Iterator, Optional

# Compound statements and the part of each that is its header line(s).
HEADER_END = {
    ast.If: lambda node: node.test,
    ast.While: lambda node: node.test,
    ast.For: lambda node: node.iter,
    ast.AsyncFor: lambda node: node.iter,
}


class LineValues:
    """
    The namespace just ``before`` and just ``after`` each statement of
    ``source``, keyed by the statement's first line. ``line_offset`` is added to
    the source's line numbers to give the line numbers of the running code (for
    a function body taken from its file).
    """

    def __init__(self, source: str, line_offset: int = 0):
        tree = ast.parse(source)
        self.line_offset = line_offset
        self.names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.statement_of_line: dict[int, int] = {}
        self.loop_headers: set[int] = set()
        self._map_statements(tree.body)
        self.before: dict[int, dict] = {}
        self.after: dict[int, dict] = {}
        self._current: Optional[int] = None

    def _map_statements(self, body: list) -> None:
        """Map each line to the first line of the innermost statement on it."""
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
                self.statement_of_line.setdefault(line, stmt.lineno)
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(stmt, field, None)
                if isinstance(inner, list) and inner and isinstance(inner[0], ast.stmt):
                    self._map_statements(inner)
            for handler in getattr(stmt, "handlers", []):
                self._map_statements(handler.body)

    def record(self, frame: FrameType) -> None:
        """A line event: the statement that ran ends, the next one starts."""
        statement = self.statement_of_line.get(frame.f_lineno - self.line_offset)
        if statement is None or statement == self._current:
            return
        snapshot = self._snapshot(frame)
        if self._current is not None:
            self.after[self._current] = snapshot
        if statement in self.loop_headers:
            # A loop's header runs again on every pass; its values are the ones
            # it started with.
            self.before.setdefault(statement, snapshot)
        else:
            self.before[statement] = snapshot
        self._current = statement

    def finish(self, frame: FrameType) -> None:
        """A traced frame returns: its last statement ends."""
        if self._current is not None:
            self.after[self._current] = self._snapshot(frame)
        self._current = None

    def _snapshot(self, frame: FrameType) -> dict:
        f_locals, f_globals = frame.f_locals, frame.f_globals
        snapshot = {}
        for name in self.names:
            if name in f_locals:
                snapshot[name] = f_locals[name]
            elif name in f_globals:
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

    def on_line(code, line):
        values.record(sys._getframe(1))

    def on_return(code, offset, retval):
        values.finish(sys._getframe(1))

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
    def trace_lines(frame: FrameType, event: str, arg) -> Callable:
        if event == "line":
            values.record(frame)
        elif event == "return":
            values.finish(frame)
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
