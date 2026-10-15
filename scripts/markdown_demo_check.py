"""
Render the HandCalcs demo with MarkdownRenderer, run structural checks on it and
write a notebook for checking by eye in Jupyter front-ends (JupyterLab, Notebook 7,
VS Code, Colab). Prints the Markdown, then any problems found:

- LaTeX text-mode commands leaking into the Markdown;
- a ``$$`` math group that is not on a single line;
- each math paragraph's blockquote depth, as parsed by markdown-it.

The notebook (``markdown_demo.ipynb``) holds the demo as one Markdown cell, then a
``%%render`` cell of a small nested example for a live check. It is written to the
output directory (default: ./markdown_demo_build).

    uv run python scripts/markdown_demo_check.py [out_dir]
"""
import pathlib
import sys

import nbformat
from markdown_it import MarkdownIt

from handcalcs import HandCalcs
from handcalcs.renderers import MarkdownRenderer

LEAKS = ("\\medskip", "\\noindent", "\\begin{list}", "\\end{list}", "\\section", "<br>")

LIVE_CELL = '''%%render
a = 2
b = 3
if a < b:
    c = a + b # inline comment
    if c > 4:
        d = c ** 2
    e = d / 2
f = e - 1
'''


def problems(markdown: str) -> list[str]:
    found = [f"leaked LaTeX: {leak}" for leak in LEAKS if leak in markdown]
    for number, line in enumerate(markdown.splitlines(), 1):
        if line.lstrip("> ").startswith("$$") and line.count("$$") != 2:
            found.append(f"line {number}: math group not on one line: {line[:60]}")
    return found


def math_depths(markdown: str) -> list[tuple[int, str]]:
    """``(blockquote depth, start of content)`` for every math paragraph."""
    depth, depths = 0, []
    for token in MarkdownIt().parse(markdown):
        if token.type == "blockquote_open":
            depth += 1
        elif token.type == "blockquote_close":
            depth -= 1
        elif token.type == "inline" and token.content.startswith("$$"):
            depths.append((depth, token.content[:70]))
    return depths


def main(out_dir: pathlib.Path) -> int:
    markdown = HandCalcs(renderer=MarkdownRenderer()).demo()
    print(markdown)
    print("-" * 72)
    for depth, content in math_depths(markdown):
        print(f"depth {depth}: {content}")
    found = problems(markdown)
    for problem in found:
        print(f"PROBLEM: {problem}")

    out_dir.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [
        nbformat.v4.new_code_cell("import handcalcs"),
        nbformat.v4.new_markdown_cell(markdown),
        nbformat.v4.new_code_cell(LIVE_CELL),
    ]
    path = out_dir / "markdown_demo.ipynb"
    nbformat.write(notebook, path)
    (out_dir / "markdown_demo.md").write_text(markdown)
    print(f"{len(found)} problem(s). Notebook written to {path}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "markdown_demo_build")))
