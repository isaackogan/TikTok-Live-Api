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
    "sphinx_sitemap",
    "sphinxext.opengraph",
]

html_logo = "logo.png"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

html_theme = "furo"

# Furo's defaults, copied verbatim from its theme.conf, with our attribution
# block inserted after navigation. Overriding html_sidebars replaces the whole
# list, so omitting any entry here silently removes it from the sidebar.
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/eulerstream.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
        "sidebar/variant-selector.html",
    ]
}

# The single highest-leverage on-page string on the site. Keyword-led, and
# deliberately free of the version number so the <title> is stable across
# releases (a churning title resets accumulated relevance).
html_title = "TikTok LIVE API for Python — TikTokLive Documentation"
html_short_title = "TikTokLive Docs"

# Required for canonical tags and by sphinx-sitemap. Must match the live
# Pages URL exactly, trailing slash included.
html_baseurl = "https://isaackogan.github.io/TikTokLive/"

# -- Sitemap ------------------------------------------------------------------
# The default scheme is "{lang}{version}{link}", which emits broken URLs when
# neither language nor version dirs are in use. "{link}" is what a flat,
# single-version site needs.
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap.xml"

# Utility and stub pages carry no unique crawlable content — search.html is
# even stamped noindex by Furo — so they are not advertised in the sitemap.
# modules.html is a 7-line stub whose entire body is one toctree link.
sitemap_excludes = [
    "search.html",
    "genindex.html",
    "py-modindex.html",
    "modules.html",
]

# -- Open Graph / social cards -------------------------------------------------
ogp_site_url = html_baseurl
ogp_site_name = "TikTokLive Documentation"
ogp_type = "website"
ogp_image = (
    "https://raw.githubusercontent.com/isaackogan/TikTokLive"
    "/master/.github/SquareLogo.png"
)
ogp_image_alt = "TikTokLive — TikTok LIVE API for Python"
ogp_description_length = 200
ogp_enable_meta_description = True
ogp_custom_meta_tags = [
    '<meta name="twitter:card" content="summary_large_image" />',
]

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

# Files copied verbatim to the site root. Used for the Google Search Console
# verification file, which must be served at an exact path.
html_extra_path = ["extra"]

html_permalinks_icon = "#"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown"
}
