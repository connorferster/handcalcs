"""Symbol and function translations for the "Symbols and functions" page."""
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer
from handcalcs.renderers.ascii import swap_greeks


class LnHTMLRenderer(HTMLRenderer):
    """log(...) shown as ln(...)."""


@LnHTMLRenderer.register("function_call:pre")
def swap_ln(renderer, node, base_context):
    if node.function_name.identifier == "log":
        node.function_name.identifier = "ln"
        node.function_name.value = "ln"
    return node


class TimesHTMLRenderer(HTMLRenderer):
    """× instead of · for multiplication."""


@TimesHTMLRenderer.register("mult_op:pre")
def times_sign(renderer, node, base_context):
    node.symbol = "×"
    return node


class NoGreekTextRenderer(ASCIIRenderer):
    """ASCII output with Greek names left as written."""


NoGreekTextRenderer.rule_handlers["name"]["sym"].remove(swap_greeks)
