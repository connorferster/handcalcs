"""
Showing a render where the code is running: in a Jupyter kernel, as rich output;
anywhere else, as printed text. Used by ``@handcalc(display=True)`` and by the
Jupyter interface. IPython is optional and is only imported inside a kernel.
"""

__all__ = ["show", "display_class_for", "DISPLAY_CLASS_NAMES"]

from typing import Any

from ..renderers.base import BaseRenderer

# The IPython.display class for each built-in renderer's output. A custom
# renderer uses the display class of its nearest built-in ancestor.
DISPLAY_CLASS_NAMES = {
    "markdown": "Markdown",
    "latex": "Latex",
    "html": "HTML",
    "ascii": "Pretty",
    "base": "Pretty",
}


def display_class_for(renderer_cls: type[BaseRenderer]) -> type:
    """
    The IPython display class of the renderer's nearest built-in ancestor (or
    itself); ``Pretty`` for a renderer with none. Needs IPython.
    """
    import IPython.display

    for cls in renderer_cls.__mro__:
        name = cls.__dict__.get("name")
        if name in DISPLAY_CLASS_NAMES:
            return getattr(IPython.display, DISPLAY_CLASS_NAMES[name])
    return IPython.display.Pretty


def in_kernel() -> bool:
    """True in a Jupyter kernel (a notebook, JupyterLab, VS Code, Colab)."""
    try:
        from IPython import get_ipython
    except ImportError:
        return False
    # Terminal IPython has no kernel: it shows a Markdown object as its repr.
    return getattr(get_ipython(), "kernel", None) is not None


def show(renderer: BaseRenderer, rendered: Any) -> None:
    """
    Show ``rendered``, the output of ``renderer``: displayed with the renderer's
    display class in a Jupyter kernel, printed elsewhere. Output that is not text
    (a Word document, an Excel workbook) can't be shown; write it to a file.
    """
    if not isinstance(rendered, str):
        raise TypeError(
            f"{type(renderer).__name__} renders a {type(rendered).__name__}, not "
            "text, so it can't be displayed; give a destination to write it to a "
            "file."
        )
    if in_kernel():
        from IPython.display import display

        display(display_class_for(type(renderer))(rendered))
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
