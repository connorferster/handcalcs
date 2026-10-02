from .renderers import BaseRenderer, PlainTextRenderer, get_renderer
from .config import set_option, save_config, get_config, get_option, reset_option, reset_config
from .interfaces.object_oriented import HandCalcs
from .interfaces.decorator import handcalc

# Import the Jupyter interface only when within an IPython environment
try:
    from IPython import get_ipython
    ip = get_ipython()
    from .interfaces.jupyter import render, hc_default_renderer, hc_format_code
except AttributeError:
    pass