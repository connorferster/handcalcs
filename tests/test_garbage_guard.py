"""
Garbage-output guard (rc1 release review, section 6.9): everyday snippets run
through every renderer. A snippet may render a line or leave it out, but it must
never raise, leak a Python repr (``<... at 0x...>``, ``NoValue``, a parse node),
show an empty step (``a =  = 3``) or leave ``{{ }}`` unfilled.

To guard a new kind of line, add a snippet to CORPUS.
"""
import re

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

# name -> (source, modules it needs)
CORPUS = {
    "arithmetic": ("a = 2\nb = 3.5\nc = a*b + a**2/b - 1\n", ()),
    "parameters": ("L = 6.0\nloads = [1.2, 3.4]\nk = -2.5\n", ()),
    "parameter_grid": ("a = 1; b = 2; c = 3\n", ()),
    "skip_substitution": ("a = 2\nb = 3\nd = (a**2 + b**2)\n", ()),
    "reassignment": ("a = 2\nb = a * 3\na = 10\nc = a * 3\n", ()),
    "augmented": ("a = 1\nb = 2\na += b\na *= b + 1\n", ()),
    "chained": ("a = b = 3\nc = a + b\n", ()),
    "unpacking": ("a, b = 1, 2\nc = a + b\n", ()),
    "starred": ("first, *rest = [1, 2, 3]\nn = len(rest)\n", ()),
    "negative_power": ("a = -2\nb = a**2\nc = (-a)**0.5\n", ()),
    "floor_mod": ("a = 7\nb = a // 2\nc = a % 2\n", ()),
    "big_small": ("a = 1e-12\nb = 123456789.0\nN = 10**12\nE = 200000\nc = a*b\n", ()),
    "format_code": ("E = 200e9\nI = 1.5e-4\nk = E*I  # hc: -f .3e\n", ()),
    "complex": ("z = 3 + 4j\nw = abs(z)\n", ()),
    "bool_ops": ("a = 3\nb = a > 2 and a < 5\nc = not b\n", ()),
    "compare_chain": ("a = 3\nok = 1 < a <= 5\nsame = a == 3\n", ()),
    "check": ("M_Rd = 100\nM_Ed = 80\nM_Ed <= M_Rd  # hc: --check\n", ()),
    "if_expression": ("a = 2\nb = 10 if a > 0 else -10\n", ()),
    "math_functions": (
        "from math import sqrt, sin, cos, radians, pi, log, exp\n"
        "alpha = 30\nd = sqrt(2) * sin(radians(alpha)) + cos(pi / 3)\ne = log(exp(2))\n",
        (),
    ),
    "builtins": ("xs = [3, 1, 2]\nm = max(xs) - min(xs)\nr = round(2.567, 2)\nn = len(xs)\n", ()),
    "keyword_args": ("r = round(2.567, ndigits=2)\ns = sorted([3, 1], reverse=True)\n", ()),
    "module_attribute": ("import math\nc = 2 * math.pi\n", ()),
    "expression_line": ("a = 3\n2 * a + 1\nabs(-a)\n", ()),
    "strings": ("name = 'W310x39'\ngrade = name + '-350W'\nt = f'{name} steel'\n", ()),
    "none": ("a = None\n", ()),
    "lambda": ("f = lambda x: x * 2\ny = f(3)\n", ()),
    "comprehensions": (
        "xs = [1, 2, 3]\nys = [x**2 for x in xs if x > 1]\n"
        "d = {x: x * 2 for x in xs}\ns = sum(x**2 for x in xs)\n",
        (),
    ),
    "indexing": (
        "xs = [1, 2, 3]\ni = 1\nd = {'a': 1}\n"
        "y = xs[0] + xs[-1] + xs[i] + xs[i + 1]\nz = d['a'] * 3\nw = xs[1:]\n",
        (),
    ),
    "method_calls": ("s = 'abc'\nu = s.upper()\nn = s.count('a')\n", ()),
    "attribute_of_expression": ("z = 3 + 4j\nr = (z * 2).real\n", ()),
    "conditional": (
        "a = 5\nif a > 3:\n    b = a*2\nelif a > 1:\n    b = a\nelse:\n    b = 0\n",
        (),
    ),
    "conditional_none_true": ("a = 0\nif a > 3:\n    b = 1\nelif a > 1:\n    b = 2\n", ()),
    "conditional_reassigned_test": ("a = 5\nif a > 3:\n    a = 1\n    b = a\n", ()),
    "for_loop": ("t = 0\nfor i in range(3):\n    t = t + i\n", ()),
    "for_unpack": ("t = 0\nfor i, x in enumerate([4, 5]):\n    t = t + i * x\n", ()),
    "loop_with_if": ("n = 0\nfor x in [1, 5, 9]:\n    if x > 4:\n        n = n + 1\n", ()),
    "while_def_class_try": (
        "def f(x):\n    return x * 2\n\nclass C:\n    k = 1\n\n"
        "i = 0\nwhile i < 2:\n    i = i + 1\ntry:\n    j = 1\nexcept ValueError:\n    j = 0\n"
        "y = f(3) + C.k + i + j\n",
        (),
    ),
    "with_block": ("import decimal\nwith decimal.localcontext():\n    a = 3\n    b = a * 2\n", ()),
    "print_and_imports": ("import math\nfrom math import sqrt\na = sqrt(4)\nprint(a)\n", ()),
    "comments": (
        "## Heading\n### Subheading\n# Prose about a 50% load\n"
        "a = 3  # length\n# a is {{ a }}\nb = a * 2  # twice {{ a }}\n",
        (),
    ),
    "comment_commands": (
        "# hc: -h\nL = 6.0  # span\nw = 2.0  # load\n\n"
        "M = w * L**2 / 8  # hc: -m\nx = M * 2  # hc: -p\ny = x + 1  # hc: -i\nz = M  # hc: -f .1f\n",
        (),
    ),
    "greek_and_subscripts": ("alpha = 3\nsigma_max = alpha * 2\nN_pl_Rd = 1.5\nβ = 2\n", ()),
    "decimal": ("from decimal import Decimal\na = Decimal('1.10')\nb = a*2\n", ()),
    "pint": (
        "import pint\nureg = pint.UnitRegistry()  # hc: -i\n"
        "L = 6 * ureg.m\nw = 5 * ureg.kN / ureg.m\nM = w * L**2 / 8\nM2 = M.to('kN*m')\n"
        "v = (L * 2).magnitude\ntheta = 30 * ureg.degree\n",
        ("pint",),
    ),
    "pint_offset": (
        "import pint\nureg = pint.UnitRegistry()  # hc: -i\n"
        "T = ureg.Quantity(20, ureg.degC)\nT2 = T.to(ureg.degF)\n",
        ("pint",),
    ),
    "forallpeople": (
        "import forallpeople as si\nsi.environment('structural')  # hc: -i\n"
        "L = 6 * si.m\nw = 5 * si.kN / si.m\nM = w * L**2 / 8\nR = w * L / 2\n",
        ("forallpeople",),
    ),
    "numpy": (
        "import numpy as np\nx = np.array([1.0, 2.0, 3.0])\ny = np.sqrt(x) * 2\n"
        "z = np.sum(y)  # hc: -f .2f\nm = x.mean()\nA = np.array([[1, 2], [3, 4]])\nB = A @ A\nb = A[0, 1]\n",
        ("numpy",),
    ),
}

TEXT_RENDERERS = {
    "ascii": ASCIIRenderer,
    "html": HTMLRenderer,
    "latex": LatexRenderer,
    "markdown": MarkdownRenderer,
}

# Python reprs and parse-tree objects that must never reach a reader.
LEAKS = re.compile(
    r" at 0x[0-9a-f]+|NoValue|NotImplemented|<function |<lambda>|<generator "
    r"|<built-in |identifier=|deque\(|Traceback|\{\{\s*[A-Za-z_][\w.]*\s*\}\}"
)


def render(renderer, case: str):
    source, needs = CORPUS[case]
    for module in needs:
        pytest.importorskip(module)
    return HandCalcs(renderer())(source)


def empty_steps(text: str, equals: str) -> list[str]:
    """The lines of 'text' with an empty step between two of their '=' signs."""
    # '==' is Python's equality operator, rendered as written.
    pattern = re.compile(rf"(?<!{equals}){equals}\s+{equals}(?!{equals})|{equals}\s*$")
    return [line for line in text.splitlines() if pattern.search(line)]


@pytest.mark.parametrize("case", CORPUS)
@pytest.mark.parametrize("renderer", TEXT_RENDERERS)
def test_text_renderers_render_everyday_python_cleanly(renderer, case):
    output = render(TEXT_RENDERERS[renderer], case)
    assert isinstance(output, str) and output.strip()
    assert not LEAKS.findall(output)
    if renderer == "ascii":
        # A line with an empty step; a '# hc: -m' row starts with '=' on purpose.
        steps = [line.strip() for line in output.splitlines() if " = " in line]
        steps = [line.removeprefix("= ") for line in steps]
        assert not [line for line in steps if any(not s.strip() for s in line.split(" = "))]
    elif renderer in ("latex", "markdown"):
        # One row of an aligned block per line, ending at '\\' or '\end{aligned}'.
        rows = re.split(r"\\\\|\\end\{aligned\}", output)
        assert not empty_steps("\n".join(row.strip() for row in rows), "=")
    else:
        text = re.sub(r"<[^>]+>", " ", output)
        assert not empty_steps(text, "=")


@pytest.mark.parametrize("case", CORPUS)
def test_word_renders_everyday_python_cleanly(case):
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    document = render(WordRenderer, case)
    text = "".join(re.findall(r"<(?:m|w):t(?: [^>]*)?>([^<]*)<", document.element.xml))
    assert text.strip()
    assert not LEAKS.findall(text)


@pytest.mark.parametrize("case", CORPUS)
def test_excel_renders_or_rejects_cleanly(case):
    """A worksheet holds only assignments: anything else must be a clear rejection."""
    pytest.importorskip("xlsxwriter")
    from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError

    try:
        workbook = render(ExcelRenderer, case)
    except ExcelRendererIncompatibleError:
        return
    for row in workbook.rows:
        assert not LEAKS.findall(repr(getattr(row, "value", "")))
        assert not LEAKS.findall(repr(getattr(row, "cached", "")))
