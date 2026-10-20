from .renderers import BaseRenderer, PlainTextRenderer, get_renderer
from .config import (
    set_option,
    save_config,
    get_config,
    get_option,
    reset_option,
    reset_config,
)
from .interfaces.object_oriented import HandCalcs
from .interfaces.decorator import handcalc
from .parsing.inputs import find_inputs

# Import the Jupyter interface (the %%render magic) only inside a running IPython
# shell. IPython is optional: without it, or in a plain Python process,
# handcalcs works through HandCalcs and @handcalc alone.
try:
    from IPython import get_ipython
except ImportError:
    get_ipython = None

if get_ipython is not None and get_ipython() is not None:
    from .interfaces.jupyter import render, hc_default_renderer, hc_format_code
