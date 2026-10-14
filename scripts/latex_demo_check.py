"""
Render the HandCalcs demo with LatexRenderer, wrap it in a minimal amsmath
document and compile it with pdflatex. Prints the LaTeX, then any pdflatex
errors and every overfull box (output wider than the text width), with the
first line of the source it came from. The PDF is written to the output directory (default: ./latex_demo_build).

    uv run python scripts/latex_demo_check.py [out_dir]
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys

from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

PREAMBLE = "\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n"
POSTAMBLE = "\\end{document}\n"
OVERFULL = re.compile(r"^Overfull \\hbox \((?P<amount>[\d.]+)pt too wide\) .*at lines? (?P<start>\d+)")


def overfull_boxes(log: str, tex_lines: list[str]) -> list[tuple[float, int, str]]:
    """
    ``(points too wide, tex line, first non-wrapper source line)`` for every
    overfull hbox in a pdflatex log.
    """
    boxes = []
    for line in log.splitlines():
        match = OVERFULL.match(line)
        if not match:
            continue
        start = int(match["start"])
        source = next(
            (text for text in tex_lines[start - 1:]
             if text.strip() and not text.startswith(("\\noindent$", "\\begin{aligned}", "\\medskip"))),
            "",
        )
        boxes.append((float(match["amount"]), start, source))
    return boxes


def find_pdflatex() -> str | None:
    found = shutil.which("pdflatex")
    if found:
        return found
    tinytex = pathlib.Path.home() / ".TinyTeX" / "bin" / "x86_64-linux" / "pdflatex"
    return str(tinytex) if tinytex.exists() else None


def main() -> int:
    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "latex_demo_build")
    out_dir.mkdir(parents=True, exist_ok=True)
    body = HandCalcs(renderer=LatexRenderer()).demo()
    print(body)
    tex = out_dir / "demo.tex"
    tex.write_text(PREAMBLE + body + POSTAMBLE)
    pdflatex = find_pdflatex()
    if pdflatex is None:
        print("pdflatex not found; skipped compilation")
        return 1
    result = subprocess.run(
        [pdflatex, "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=out_dir, capture_output=True, text=True,
    )
    errors = [line for line in result.stdout.splitlines() if line.startswith("!") or "Warning" in line]
    print("\n".join(errors) if errors else "--- compiled OK, no errors/warnings ---")
    log = (out_dir / "demo.log").read_text(errors="replace")
    boxes = overfull_boxes(log, tex.read_text().splitlines())
    for amount, start, source in boxes:
        print(f"OVERFULL {amount:6.1f}pt  line {start}: {source[:90]}")
    if not boxes:
        print("--- no overfull boxes ---")
    print(f"PDF: {out_dir / 'demo.pdf'} (exit {result.returncode})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
