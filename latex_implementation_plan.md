# LatexRenderer implementation plan / session notes

Branch: `features/latex_renderer`

## Standing instructions from the user (2026-10-14)
- The user is mid-implementation of `LatexRenderer` (`src/handcalcs/renderers/latex.py`) and is happy with
  progress so far. The goal now is to evaluate and fix the "funny behaviours" in the output.
- Evaluate progress by running the demo:
  ```
  uv run python -c "from handcalcs import HandCalcs; from handcalcs.renderers import LatexRenderer; hc = HandCalcs(renderer=LatexRenderer()); import rich; rich.print(hc.demo())"
  ```
- **Ignore `tests/test_latex_renderer.py`** — those were token tests that an earlier Claude session wrote. Focus on the demo output.
- Sessions may disconnect: keep this file up to date and commit + push frequently.

## Status
_(updated as work progresses — see sections below)_

## Observed issues in demo output
_TBD_

## Plan / fixes done
_TBD_
