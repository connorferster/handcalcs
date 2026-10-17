"""
The ``src`` role: link a Python object to its source lines on GitHub.

    {src}`handcalcs.renderers.base.render_calcline`
    {src}`the calc line handler <handcalcs.renderers.base.render_calcline>`

The object is imported at build time and its lines are found with ``inspect``,
so links follow the code as it moves. The link points at ``hc_source_ref`` in
``hc_repo_url`` (both set in conf.py).
"""

import importlib
import inspect
import pathlib

from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxRole

logger = logging.getLogger(__name__)


def resolve(dotted: str):
    """Import the longest importable module prefix of ``dotted``, then getattr the rest."""
    parts = dotted.split(".")
    for split in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        for attr in parts[split:]:
            obj = getattr(obj, attr)
        return obj
    raise ImportError(dotted)


class SourceRole(SphinxRole):
    def run(self):
        text = self.text
        if "<" in text and text.endswith(">"):
            label, target = text[:-1].split("<", 1)
            label = label.strip()
        else:
            label, target = f"{text.rsplit('.', 1)[-1]}", text
        target = target.strip()
        config = self.env.config
        repo_root = pathlib.Path(self.env.srcdir).parent.resolve()
        try:
            obj = inspect.unwrap(resolve(target))
            path = pathlib.Path(inspect.getsourcefile(obj)).resolve()
            relative = path.relative_to(repo_root).as_posix()
            if inspect.ismodule(obj):
                anchor = ""
            else:
                lines, start = inspect.getsourcelines(obj)
                anchor = f"#L{start}-L{start + len(lines) - 1}"
        except Exception as error:  # report and fall back to plain code text
            logger.warning(f"src role: cannot resolve {target!r}: {error}", location=self.get_location())
            return [nodes.literal(label, label)], []
        url = f"{config.hc_repo_url}/blob/{config.hc_source_ref}/{relative}{anchor}"
        ref = nodes.reference("", "", internal=False, refuri=url, classes=["hc-src"])
        ref += nodes.literal(label, label)
        return [ref], []


def setup(app):
    app.add_config_value("hc_repo_url", "", "env")
    app.add_config_value("hc_source_ref", "main", "env")
    app.add_role("src", SourceRole())
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
