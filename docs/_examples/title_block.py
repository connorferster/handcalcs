"""A title block at the top of every calculation (#137)."""
from handcalcs.renderers import LatexRenderer, MarkdownRenderer

FIELDS = (("project", "Project"), ("calc_by", "By"), ("checked_by", "Checked"), ("date", "Date"))


def title_rows(base_context):
    """(label, value) for each title field that is set, from config or '# hc:' commands."""
    context = base_context.global_context
    return [(label, getattr(context, name)) for name, label in FIELDS if hasattr(context, name)]


class TitleMarkdownRenderer(MarkdownRenderer):
    name = "title_markdown"

    def complete(self, tree, base_context):
        body = super().complete(tree, base_context)
        rows = title_rows(base_context)
        if not rows:
            return body
        table = "| " + " | ".join(label for label, _ in rows) + " |\n"
        table += "|" + "---|" * len(rows) + "\n"
        table += "| " + " | ".join(str(value) for _, value in rows) + " |\n\n"
        return table + body


class TitleLatexRenderer(LatexRenderer):
    name = "title_latex"

    def complete(self, tree, base_context):
        body = super().complete(tree, base_context)
        rows = title_rows(base_context)
        if not rows:
            return body
        cells = " & ".join(f"\\textbf{{{label}:}} {value}" for label, value in rows)
        header = (
            "\\noindent\\begin{tabular}{" + "l" * len(rows) + "}\n"
            + cells + "\n\\end{tabular}\n\n\\noindent\\hrulefill\n\n"
        )
        return header + body
