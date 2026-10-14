"""
Render the HandCalcs demo with LatexRenderer, wrap it in a minimal amsmath
document and compile it with pdflatex. Prints the LaTeX, then any pdflatex
errors. The PDF is written to the output directory (default: ./latex_demo_build).

    uv run python scripts/latex_demo_check.py [out_dir]
"""
import os
import pathlib
import shutil
import subprocess
import sys

from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

PREAMBLE = "\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n"
POSTAMBLE = "\\end{document}\n"


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
    print(f"PDF: {out_dir / 'demo.pdf'} (exit {result.returncode})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
