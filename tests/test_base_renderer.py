"""
Tests for the ``BaseRenderer`` machinery itself, independent of any single
node handler: dispatch, the class-vs-instance handler registry, classifier
parsing, context layering, and the sym/num rule pipelines.

Bugs discovered while writing these tests are documented with
``pytest.mark.xfail(strict=True)`` so the suite records current behavior and
notifies (via an unexpected pass) when a bug is fixed.
"""
from collections import deque

import pytest

from handcalcs.renderers.base import (
    BaseRenderer,
    RenderContext,
    BaseRenderContext,
)
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.sequence import HcSequence


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def test_render_routes_root_to_render_root(renderer):
    root = HcSequence(deque([Constant(1), Constant(2)]))
    parts = renderer.render(root)
    # render_root returns a list of parts, one per sequence node (+ pre/post).
    assert isinstance(parts, list)
    assert parts == ["1", "2"]


def test_render_node_dispatches_by_type(render):
    assert render(Constant(4)) == "4"


def test_unknown_node_type_raises_not_implemented(render):
    # A node whose ``type`` has no registered handler is a programming error,
    # not something to silently stringify: render_node raises NotImplementedError.
    class Mystery:
        type = "no_such_handler"

        def __repr__(self):
            return "MYSTERY"

    with pytest.raises(NotImplementedError):
        render(Mystery())


def test_render_creates_default_context_when_none_given(renderer):
    # Constant does not require line context, so a bare render must work.
    assert renderer.render(Constant(7)) == "7"


# ---------------------------------------------------------------------------
# Registry: instance vs class isolation
# ---------------------------------------------------------------------------

def test_register_handler_is_instance_scoped(renderer):
    renderer.register_handler("faketype", lambda rn, node, ctx: "X")
    assert "faketype" in renderer._handlers
    assert "faketype" not in BaseRenderer.node_handlers


def test_register_classmethod_scopes_to_subclass():
    class SubR(BaseRenderer):
        pass

    @SubR.register("mytype")
    def _handler(rn, node, ctx):  # noqa: ARG001
        return "ok"

    assert "mytype" in SubR.node_handlers
    assert "mytype" not in BaseRenderer.node_handlers


def test_subclass_gets_independent_handler_copies():
    class SubR(BaseRenderer):
        pass

    SubR.node_handlers["only_on_sub"] = lambda *a: "s"
    assert "only_on_sub" not in BaseRenderer.node_handlers


# ---------------------------------------------------------------------------
# Classifier parsing in register_handler
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "prefix,target_attr",
    [
        ("pre", "_root_pre_renderers"),
        ("post", "_root_post_renderers"),
        ("sym", "_symbolic_rules"),
        ("num", "_numeric_rules"),
    ],
)
def test_register_handler_routes_prefixes(renderer, prefix, target_attr):
    renderer.register_handler(f"{prefix}:thing", lambda *a: None)
    assert "thing" in getattr(renderer, target_attr)


def test_register_handler_bare_name_is_node_handler(renderer):
    renderer.register_handler("some_node", lambda *a: None)
    assert "some_node" in renderer._handlers


def test_register_handler_unknown_prefix_raises(renderer):
    with pytest.raises(NotImplementedError):
        renderer.register_handler("bogus:thing", lambda *a: None)


def test_register_handler_two_colons_treated_as_node_name(renderer):
    # Only a single colon triggers prefix routing; otherwise it is a node name.
    renderer.register_handler("a:b:c", lambda *a: None)
    assert "a:b:c" in renderer._handlers


# ---------------------------------------------------------------------------
# Context layering
# ---------------------------------------------------------------------------

def test_current_overlays_line_over_global():
    base = BaseRenderContext(
        RenderContext(mode="full", format_code=".5g"),
        RenderContext(mode="sym"),
    )
    # Line context wins for shared keys...
    assert base.current.mode == "sym"
    # ...and global-only keys remain visible.
    assert base.current.format == ".5g"


def test_render_context_union_merges_fields():
    a = RenderContext(mode="full")
    b = RenderContext(mode="sym", format_code=".2f")
    merged = a | b
    assert merged.mode == "sym"
    assert merged.format == ".2f"
    # space must remain the string default, not become a dict.
    assert merged.space == " "


# ---------------------------------------------------------------------------
# Rule pipelines
# ---------------------------------------------------------------------------

def test_root_pre_and_post_renderers_wrap_sequence(renderer):
    renderer.register_handler("pre:banner", lambda rn, root, ctx: "PRE")
    renderer.register_handler("post:footer", lambda rn, root, ctx: "POST")
    root = HcSequence(deque([Constant(1)]))
    parts = renderer.render(root)
    assert parts[0] == "PRE"
    assert parts[-1] == "POST"
    assert "1" in parts


def test_instance_registered_sym_rule_is_applied(renderer):
    seen = []

    def spy(node, base_context):
        seen.append(node.type)
        return node

    renderer.register_handler("sym:spy", spy)
    base = BaseRenderContext(
        RenderContext(mode="full", format_code=".5g"),
        RenderContext(current_mode="sym"),
    )
    renderer.render(Constant(1), base)
    assert seen == ["constant"]
