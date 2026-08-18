# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import importlib
# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import re
from pathlib import Path

# Single source of truth: the file release.yml stamps on every release.
# Reading it textually (rather than importing TikTokLive) keeps conf.py
# importable without the package's runtime dependencies installed.
_VERSION_FILE = Path(__file__).resolve().parents[2] / "TikTokLive" / "__version__.py"
_VERSION_MATCH = re.search(
    r'PACKAGE_VERSION\s*:\s*str\s*=\s*"([^"]+)"', _VERSION_FILE.read_text()
)
if _VERSION_MATCH is None:
    raise RuntimeError(f"Could not parse PACKAGE_VERSION from {_VERSION_FILE}")

version = release = _VERSION_MATCH.group(1)

sys.path.insert(0, os.path.abspath('../../'))

# -- Project information -----------------------------------------------------

project = 'TikTokLive'
copyright = '2022, Isaac Kogan'
author = 'Isaac Kogan'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "myst_parser",
    "sphinx_rtd_theme",
    'sphinx_search.extension',
]

html_logo = "logo.png"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

html_theme = "furo"

# The single highest-leverage on-page string on the site. Keyword-led, and
# deliberately free of the version number so the <title> is stable across
# releases (a churning title resets accumulated relevance).
html_title = "TikTok LIVE API for Python — TikTokLive Documentation"
html_short_title = "TikTokLive Docs"

# Required for canonical tags and by sphinx-sitemap. Must match the live
# Pages URL exactly, trailing slash included.
html_baseurl = "https://isaackogan.github.io/TikTokLive/"

html_theme_options = {
    "light_css_variables": {
    },
    "dark_css_variables": {
        "color-problematic": "#80aeef",
        "sidebar-filter": "invert(0.95)"
    },
    "sidebar_hide_name": True,
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['Thumbs.db', '.DS_Store', "tiktok_schema_pb2.py", "./README.md"]

# -- Options for HTML output -------------------------------------------------

html_css_files = [
    "css/custom.css"
]
html_js_files = [
]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']
html_permalinks_icon = "#"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown"
}
