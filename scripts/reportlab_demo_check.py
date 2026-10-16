"""
Render the HandCalcs demo with ym_handcalcs.ReportLabRenderer into a PDF for
checking by eye.

The text frame is centred on a US letter page and is ``--width`` points wide
(default 252 pt, the usable width of a half-width column; 504 pt is a
half-height block at full page width). With ``--png``, every page is also
rasterized to PNG (needs pymupdf: ``uv run --with pymupdf ...``).

    uv run python scripts/reportlab_demo_check.py [--width 252] [--png] [out_dir]

Output goes to ./reportlab_demo_build by default. After the build, a layout
report lists every calc line that did not fit on one line, with the layout it
chose (see ``ym_handcalcs.flowables.CalcLine``). Lines that had to shrink or
still overflow are flagged.
"""
import argparse
import pathlib

from reportlab.platypus import KeepTogether

from handcalcs import HandCalcs
from ym_handcalcs import ReportLabRenderer, build_pdf, ensure_dejavu_registered
from ym_handcalcs.flowables import CalcBlock, CalcLine, DepthGuides
from ym_handcalcs.renderer import plain_text


def calc_lines(story) -> list[CalcLine]:
    found = []
    for flowable in story:
        while isinstance(flowable, DepthGuides):
            flowable = flowable.content
        if isinstance(flowable, KeepTogether):
            found.extend(calc_lines(flowable._content))
        elif isinstance(flowable, CalcBlock):
            found.extend(flowable.lines)
        elif isinstance(flowable, CalcLine):
            found.append(flowable)
    return found


def layout_report(story) -> list[str]:
    """One line per calc line whose layout is not a plain one-liner."""
    lines = []
    for calc in calc_lines(story):
        if calc.layout == "line":
            continue
        flag = "  <-- " if calc.layout.startswith(("shrink", "overflow")) else ""
        target = plain_text(calc.columns[0]).replace("\u00a0", " ")[:40]
        lines.append(f"  {calc.layout:<28} {target}{flag}")
    return lines


def build(width: float, out_dir: pathlib.Path) -> pathlib.Path:
    ensure_dejavu_registered()
    result = HandCalcs(renderer=ReportLabRenderer()).demo()
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"reportlab_demo_{int(width)}.pdf"
    story = result["story"]
    count = len(story)
    build_pdf(result, pdf, title="HandCalcs ReportLab demo", frame_width=width)
    print(f"{pdf}: {count} flowables, frame width {width:g} pt")
    report = layout_report(story)
    total = len(calc_lines(story))
    print(f"calc lines: {total}, not on one line: {len(report)}")
    print("\n".join(report))
    return pdf


def rasterize(pdf: pathlib.Path) -> None:
    import pymupdf

    with pymupdf.open(pdf) as document:
        for number, page in enumerate(document, 1):
            png = pdf.with_name(f"{pdf.stem}_p{number}.png")
            page.get_pixmap(dpi=110).save(png)
            print(f"  {png}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("out_dir", nargs="?", default="reportlab_demo_build")
    parser.add_argument("--width", type=float, default=252)
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    pdf = build(args.width, pathlib.Path(args.out_dir))
    if args.png:
        rasterize(pdf)


if __name__ == "__main__":
    main()
