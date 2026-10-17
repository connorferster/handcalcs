"""Sphinx configuration for the handcalcs documentation."""

import inspect
import os
import pathlib
import sys

DOCS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = DOCS_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(DOCS_DIR / "_ext"))

# Build with handcalcs' built-in defaults, never the builder's own saved config.
os.environ["HANDCALCS_CONFIG"] = str(DOCS_DIR / "_build" / "no-handcalcs-config.json")

import handcalcs  # noqa: E402

project = "handcalcs"
author = "Connor Ferster"
copyright = "2020-2026, Connor Ferster"
release = handcalcs.__dict__.get("__version__", "2.0.0rc1")
version = release

# The git ref that every source-code link points at. Set this to the release tag
# (e.g. "v2.0.0") when cutting a release so links stay pinned to that code.
HC_SOURCE_REF = os.environ.get("HC_SOURCE_REF", "hc2/dev")
HC_REPO_URL = "https://github.com/connorferster/handcalcs"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.linkcode",
    "hc_example",
    "hc_source",
]

hc_repo_url = HC_REPO_URL
hc_source_ref = HC_SOURCE_REF

source_suffix = {".md": "markdown"}
exclude_patterns = ["_build", "_old_*", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "amsmath",
    "deflist",
    "fieldlist",
    "attrs_inline",
    "attrs_block",
]
myst_heading_anchors = 3

# {source}`src/handcalcs/renderers/base.py` -> the file on GitHub at HC_SOURCE_REF.
extlinks = {
    "source": (f"{HC_REPO_URL}/blob/{HC_SOURCE_REF}/%s", "%s"),
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {"members": True, "undoc-members": False}


def linkcode_resolve(domain, info):
    """Link every autodoc entry to its source lines on GitHub at HC_SOURCE_REF."""
    if domain != "py" or not info.get("module"):
        return None
    module = sys.modules.get(info["module"])
    if module is None:
        return None
    obj = module
    for part in info["fullname"].split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    obj = inspect.unwrap(obj)
    if isinstance(obj, property):
        obj = obj.fget
    try:
        path = pathlib.Path(inspect.getsourcefile(obj)).resolve()
        lines, start = inspect.getsourcelines(obj)
    except (TypeError, OSError):
        return None
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        return None
    end = start + len(lines) - 1
    return f"{HC_REPO_URL}/blob/{HC_SOURCE_REF}/{relative.as_posix()}#L{start}-L{end}"


# -- HTML output (Shibuya) ---------------------------------------------------

html_theme = "shibuya"
html_title = "handcalcs"
html_static_path = ["_static"]
html_css_files = ["handcalcs-docs.css"]
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")

html_context = {
    "source_type": "github",
    "source_user": "connorferster",
    "source_repo": "handcalcs",
    "source_version": HC_SOURCE_REF,
    "source_docs_path": "/docs/",
}

html_theme_options = {
    "accent_color": "teal",
    "github_url": HC_REPO_URL,
    "nav_links": [
        {"title": "Get started", "url": "getting-started/index"},
        {"title": "Renderers", "url": "renderers/index"},
        {"title": "Interfaces", "url": "interfaces/index"},
        {
            "title": "Extend",
            "children": [
                {
                    "title": "Customize a renderer",
                    "url": "customizing/index",
                    "summary": "Change colors, symbols and layout of a built-in renderer",
                },
                {
                    "title": "Build a renderer",
                    "url": "building-renderers/index",
                    "summary": "Write a renderer for a new output format",
                },
                {
                    "title": "Developer's guide",
                    "url": "developers/index",
                    "summary": "Work on handcalcs itself",
                },
            ],
        },
        {"title": "Reference", "url": "reference/index"},
    ],
    "globaltoc_expand_depth": 1,
}

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
