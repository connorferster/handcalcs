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


# ---------------------------------------------------------------------------
# join: the post-render pass that inserts spacing, indent and newlines
# ---------------------------------------------------------------------------

def test_join_strings_and_component_lines(renderer):
    # A string is a whole line; an all-string list is a line whose components
    # are joined by a single space. Each line self-terminates with a newline.
    tree = ["A heading", ["c", "=", "a+2", "=", "5"]]
    assert renderer.join(tree) == "A heading\nc = a+2 = 5\n"


def test_join_indents_block_body_by_depth(renderer):
    # A [header, body] block renders the header at the current depth and its
    # body one indent level deeper; nesting compounds the indent. The tree is a
    # root list containing one block (as render_root produces).
    tree = [
        ["Since x:", [
            ["a", "=", "2"],
            ["Inner:", [["b", "=", "3"]]],
        ]],
    ]
    assert renderer.join(tree) == (
        "Since x:\n"
        "    a = 2\n"
        "    Inner:\n"
        "        b = 3\n"
    )


def test_join_skips_falsy_items(renderer):
    # Command/ignored lines render to falsy values and must not emit blank lines.
    tree = ["kept", "", None, [], ["x", "=", "1"]]
    assert renderer.join(tree) == "kept\nx = 1\n"


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

@pytest.mark.parametrize("category", ["pre", "sym", "num", "post"])
def test_register_handler_routes_categories(renderer, category):
    # A '{node_type}:{category}' classifier appends to that node type's ordered
    # rule list for the category.
    renderer.register_handler(f"faketype:{category}", lambda *a: None)
    assert category in renderer._rule_handlers.get("faketype", {})
    assert len(renderer._rule_handlers["faketype"][category]) == 1


def test_register_handler_multiple_rules_preserve_order(renderer):
    # Multiple rules registered to one node type/category run in registration
    # order.
    renderer.register_handler("faketype:sym", lambda *a: "first")
    renderer.register_handler("faketype:sym", lambda *a: "second")
    rules = renderer._rule_handlers["faketype"]["sym"]
    assert [r(None, None, None) for r in rules] == ["first", "second"]


def test_register_handler_header_still_routes(renderer):
    renderer.register_handler("header:if_block", lambda *a: "hdr")
    assert "if_block" in renderer._header_handlers


def test_register_handler_bare_name_is_node_handler(renderer):
    renderer.register_handler("some_node", lambda *a: None)
    assert "some_node" in renderer._handlers


def test_register_handler_unknown_category_raises(renderer):
    with pytest.raises(NotImplementedError):
        renderer.register_handler("faketype:thing", lambda *a: None)


def test_register_handler_two_colons_treated_as_node_name(renderer):
    # Only a single colon triggers category routing; otherwise it is a node name.
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
    # The sequence-level pre/post renderers register against the pseudo node
    # type 'root'.
    renderer.register_handler("root:pre", lambda rn, root, ctx: "PRE")
    renderer.register_handler("root:post", lambda rn, root, ctx: "POST")
    root = HcSequence(deque([Constant(1)]))
    parts = renderer.render(root)
    assert parts[0] == "PRE"
    assert parts[-1] == "POST"
    assert "1" in parts


def test_instance_registered_sym_rule_is_applied(renderer):
    # A 'sym' rule on a node type fires only while current_mode == 'sym'.
    seen = []

    def spy(rn, node, base_context):
        seen.append(node.type)
        return node

    renderer.register_handler("constant:sym", spy)
    base = BaseRenderContext(
        RenderContext(mode="full", format_code=".5g"),
        RenderContext(current_mode="sym"),
    )
    renderer.render(Constant(1), base)
    assert seen == ["constant"]


def test_registered_num_rule_only_fires_in_num_mode(renderer):
    # A 'num' rule does not fire while current_mode == 'sym'.
    seen = []

    def spy(rn, node, base_context):
        seen.append(node.type)
        return node

    renderer.register_handler("constant:num", spy)
    sym_ctx = BaseRenderContext(
        RenderContext(mode="full", format_code=".5g"),
        RenderContext(current_mode="sym"),
    )
    renderer.render(Constant(1), sym_ctx)
    assert seen == []

    num_ctx = BaseRenderContext(
        RenderContext(mode="full", format_code=".5g"),
        RenderContext(current_mode="num"),
    )
    renderer.render(Constant(1), num_ctx)
    assert seen == ["constant"]


def test_registered_post_rule_transforms_rendered_output(renderer):
    # A 'post' rule receives the rendered result and returns a replacement.
    renderer.register_handler("constant:post", lambda rn, rendered, node, ctx: f"[{rendered}]")
    assert renderer.render(Constant(4)) == "[4]"
