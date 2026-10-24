"""An HTMLRenderer with a color theme and highlighted results."""
from handcalcs.renderers import HTMLRenderer


class ThemedHTMLRenderer(HTMLRenderer):
    name = "themed_html"

    # Extra rules appended to the built-in stylesheet. They use :where() too, so
    # a host page can still override them.
    STYLE = HTMLRenderer.STYLE + (
        ".handcalcs{--hc-accent:#0f766e;--hc-muted:#6b7280;--hc-result-bg:#ccfbf1;}"
        "@media (prefers-color-scheme:dark){.handcalcs{"
        "--hc-accent:#5eead4;--hc-muted:#9ca3af;--hc-result-bg:#134e4a;}}"
        ".handcalcs :where(h1,h2,h3,h4,h5,h6){color:var(--hc-accent);}"
        ".handcalcs :where(.hc-comment){color:var(--hc-muted);font-style:italic;}"
        ".handcalcs :where(.hc-header){color:var(--hc-accent);font-weight:600;}"
        ".handcalcs :where(.hc-result){background:var(--hc-result-bg);"
        "padding:0 0.25em;border-radius:3px;font-weight:600;}"
    )


@ThemedHTMLRenderer.register("calc_line:post")
def highlight_result(renderer, rendered, node, base_context):
    """Wrap the result of a one-line calculation in <span class="hc-result">."""
    if not isinstance(rendered, list):
        return rendered  # a multi-line (# hc: -m) grid is already one string
    assign = base_context.current.assign
    positions = [i for i, part in enumerate(rendered) if part == assign]
    if len(positions) < 2:
        return rendered  # a parameter (target = value): leave inputs plain
    result = positions[-1] + 1
    rendered[result] = f'<span class="hc-result">{rendered[result]}</span>'
    return rendered
