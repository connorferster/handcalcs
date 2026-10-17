"""
Render the ExcelRenderer demo (``HandCalcs(renderer=ExcelRenderer()).demo()``)
to ``excel_demo.xlsx`` for checking by eye in Excel or LibreOffice, and print
its rows and any problems found:

- the base handcalcs demo must raise ``ExcelRendererIncompatibleError``;
- optionally, with the ``formulas`` package installed, every formula cell is
  recalculated and compared with its cached Python value, e.g.
  ``uv run --with formulas python scripts/excel_demo.py``.

The workbook is written to the output directory (default: ./excel_demo, gitignored).

    uv run python scripts/excel_demo.py [out_dir]
"""
import math
import pathlib
import sys

from handcalcs import HandCalcs
from handcalcs.renderers import demo as base_demo
from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError
from handcalcs.renderers.excel.rich_text import plain_text
from handcalcs.renderers.excel.rows import CalcRow, ParamRow


def describe(row) -> str:
    if isinstance(row, CalcRow):
        hidden = "  (hidden)" if row.hidden else ""
        return f"{plain_text(row.symbol)} = {plain_text(row.symbolic)} = {row.formula}  -> {row.cached!r}{hidden}"
    if isinstance(row, ParamRow):
        return f"{plain_text(row.symbol)} = {row.value!r}  [{row.name}]"
    return f"<{type(row).__name__}> {getattr(row, 'text', '')}"


def recalculate(path: pathlib.Path) -> dict:
    """
    Recalculate a workbook with the ``formulas`` package: ``{"E7": value}``.

    ``formulas`` does not resolve worksheet-scoped defined names (they come
    back ``#REF!``; Excel and LibreOffice resolve them), so it evaluates a copy
    with the names promoted to workbook scope.
    """
    import formulas
    import openpyxl

    workbook = openpyxl.load_workbook(path)
    for sheet in workbook.worksheets:
        for name in list(sheet.defined_names):
            defined = sheet.defined_names.pop(name)
            defined.localSheetId = None
            workbook.defined_names[name] = defined
    copy = path.with_name(path.stem + "_global_names.xlsx")
    workbook.save(copy)
    try:
        solution = formulas.ExcelModel().loads(str(copy)).finish().calculate()
    finally:
        copy.unlink()
    return {
        key.rsplit("!", 1)[-1].upper(): value.value[0, 0]
        for key, value in solution.items()
        if "!" in key and hasattr(value, "value")
    }


def recalculation_problems(path: pathlib.Path, rows: list) -> list[str]:
    try:
        computed = recalculate(path)
    except ImportError:
        print("(formulas not installed: skipping the recalculation check)")
        return []
    found = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, CalcRow):
            continue
        got = computed.get(f"E{number}")
        if isinstance(row.cached, bool):
            ok = bool(got) is row.cached
        elif isinstance(row.cached, str):
            ok = str(got) == row.cached
        else:
            try:
                ok = math.isclose(float(got), float(row.cached), rel_tol=1e-9)
            except (TypeError, ValueError):
                ok = False
        if not ok:
            found.append(f"E{number} ({row.name}): Excel {got!r} != Python {row.cached!r}")
    print(f"recalculated {sum(isinstance(r, CalcRow) for r in rows)} formula cells with 'formulas'")
    return found


def main(out_dir: str = "excel_demo") -> int:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    try:
        HandCalcs(renderer=ExcelRenderer())(base_demo.source)
        problems.append("the base demo rendered without raising")
    except ExcelRendererIncompatibleError as error:
        print(f"base demo raises as expected: {error}")

    path = out / "excel_demo.xlsx"
    result = HandCalcs(renderer=ExcelRenderer(sheet_name="Beam check", filepath=path)).demo()
    for number, row in enumerate(result.rows, 1):
        print(f"{number:3d}  {describe(row)}")
    problems += recalculation_problems(path, result.rows)
    print(f"\nwrote {path}")
    for problem in problems:
        print(f"PROBLEM: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
