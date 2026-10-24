# Testing your renderer

A renderer is a function from source code to output, which makes it easy to test: render
a known calculation and compare the result.

## Use the full pipeline

Test through `HandCalcs`, with an explicit namespace so the test does not depend on
running the code:

```python
from handcalcs import HandCalcs
from my_renderers import UnicodeRenderer


def render(source, **values):
    return HandCalcs(UnicodeRenderer())(source, values)


def test_multiplication_uses_centred_dot():
    out = render("b = a * 3", a=2, b=6)
    assert out.strip() == "b = a · 3 = 2 · 3 = 6"


def test_subscripts():
    assert render("x_1 = 2", x_1=2).strip() == "x₁ = 2"
```

Passing the namespace also lets you test values that are awkward to produce by running
code, such as large or negative numbers, or `NoValue` (leave the name out).

## Isolate the configuration

The global configuration seeds every render, and a developer's saved config would change
your results. Point `HANDCALCS_CONFIG` at a file that does not exist and reset the
in-memory config around each test:

```python
import pytest
from handcalcs import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "config.json"))
    config.reset_config()
    yield
    config.reset_config()
```

handcalcs' own tests do the same (see {source}`tests/test_jupyter.py` for the
pattern).

## Golden files

For a renderer with a lot of layout, compare against stored output ("golden" files)
rather than writing every expected string by hand. Render the built-in demo, which
exercises headings, prose, grids, long equations and nested conditionals:

```python
import pathlib
from handcalcs import HandCalcs

GOLDEN = pathlib.Path(__file__).parent / "golden" / "demo.rst"


def test_demo_matches_golden():
    out = HandCalcs(RstRenderer()).demo()
    assert out == GOLDEN.read_text()
```

When the output changes on purpose, regenerate the file, read the diff, and commit it.

## Validate the format

Where a validator exists, use it: render, then parse the output with the format's own
tools so a structural mistake fails the test.

| Format | Check with |
|---|---|
| HTML | `html.parser`, or `lxml.html` with strict parsing |
| reST | `docutils.core.publish_string(..., settings_overrides={"halt_level": 2})` |
| LaTeX | compile with `latexmk` in CI (slow; keep it to a few documents) |
| JSON | `json.loads(json.dumps(result))` and a schema |

## Test rules on their own

A rule is a plain function, so you can call it with a node and a context:

```python
from handcalcs.parsing.nodes import Name
from handcalcs.renderers.base import BaseRenderContext, RenderContext


def test_subscript_rule():
    ctx = BaseRenderContext(RenderContext(), RenderContext.sparse())
    node = unicode_subscripts(None, Name(identifier="x_1"), ctx)
    assert node.identifier == "x₁"
```

**Next:** [Publishing your renderer](publishing.md).
