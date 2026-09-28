__all__ = ["handcalc"]

from typing import Optional, Callable
from functools import wraps, update_wrapper
import inspect
import innerscope
from ..renderers.base import BaseRenderer, BaseRenderContext
from ..parsing.sequence import HcSequence
from .. import config


def handcalc(
    renderer: BaseRenderer, render_context: Optional[dict] = None
):
    if render_context is None:
        render_context = {}
    # Global config settings (format_code + any custom fields) seed the render
    # context, matching HandCalcs; 'default_renderer' is irrelevant here because
    # the renderer is supplied explicitly. An explicit render_context wins.
    context_settings = {
        key: value
        for key, value in config.get_config().items()
        if key != "default_renderer"
    }

    def handcalc_decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            func_source = inspect.getsource(func)
            # innerscope retrieves values of locals, closures, and globals
            scope = innerscope.call(func, *args, **kwargs)
            hc_ast = HcSequence.from_source(func_source, hc_globals=scope, hc_locals={})
            base_context = renderer.create_context(**(context_settings | render_context))
            rendered_tree = renderer.render(hc_ast, base_context)
            completed_render = renderer.complete(rendered_tree, base_context)
            return scope.return_value, completed_render
        return decorated
    return handcalc_decorator
