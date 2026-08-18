# SEO & Backlink Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the TikTokLive documentation site and turn it into an indexable, dofollow backlink source for `www.eulerstream.com`, then publish the rewritten README to PyPI via a 7.0.0 stable release.

**Architecture:** GitHub Pages is switched from legacy mode to workflow mode so the existing `actions/deploy-pages` build is actually served. SEO is added declaratively through Sphinx extensions and Furo template overrides in `docs/src/`, never by post-processing built HTML. A standalone verification script asserts the SEO invariants against the built output and runs as a gate inside `docs.yml`, so regressions fail the build rather than silently degrading rankings.

**Tech Stack:** Sphinx 9.x, Furo theme, `sphinx-sitemap` 2.9.0, `sphinxext-opengraph` 0.13.0, MyST parser, GitHub Actions, `gh` CLI, setuptools/PyPI trusted publishing.

**Spec:** `docs/superpowers/specs/2026-08-17-seo-backlink-design.md`

## Global Constraints

- Canonical site URL is exactly `https://isaackogan.github.io/TikTokLive/` (trailing slash). Never `TikTok-Live-Api`.
- All new docs dependencies go in `docs/src/requirements.txt` only. They must never enter `pyproject.toml` `[project].dependencies` — they must not ship in the wheel.
- Links to `eulerstream.com` emitted by our own templates must never carry `rel="nofollow"`.
- Anchor text to `eulerstream.com` must be varied. No single exact-match anchor repeated sitewide.
- Python floor is 3.10 (`requires-python = ">=3.10"`); `[tool.mypy] python_version = "3.10"` must stay in lockstep.
- Sphinx source dir is `docs/src`; build output is `docs/dist/html` (gitignored via the `dist` entry in `.gitignore`).
- The version displayed in docs must derive from `TikTokLive/__version__.py`, the single file `release.yml` stamps.
- Work happens on branch `seo/backlink-optimization`. `release.yml` enforces `master`, so the release is dispatched only after merge.

---

### Task 1: Clear the stray edit and establish a green baseline

**Files:**
- Modify: `TikTokLive/client/web/routes/fetch_signed_websocket.py:184`

**Interfaces:**
- Consumes: nothing.
- Produces: a clean working tree and a known-green test/lint baseline that every later task is measured against.

- [ ] **Step 1: Inspect the stray edit**

```bash
git diff TikTokLive/client/web/routes/fetch_signed_websocket.py
```

Expected: a single added line containing `2` at module level, with no trailing newline. This is an accidental keystroke, not intentional code.

- [ ] **Step 2: Revert it**

```bash
git checkout -- TikTokLive/client/web/routes/fetch_signed_websocket.py
git status --porcelain
```

Expected: empty output. If the file still shows as modified, stop and ask — the change may be intentional after all.

- [ ] **Step 3: Run the test suite**

```bash
python -m pytest -q
```

Expected: PASS. Record the count. If anything fails here it is pre-existing and must be reported before continuing, not fixed silently as part of this plan.

- [ ] **Step 4: Run mypy exactly as CI does**

```bash
python -m mypy --follow-imports=silent \
  TikTokLive/proto/__init__.py TikTokLive/proto/proto_utils.py \
  TikTokLive/events/custom_events.py TikTokLive/client/__init__.py \
  TikTokLive/client/ws/ws_utils.py TikTokLive/client/web/web_client.py \
  TikTokLive/client/web/web_settings.py TikTokLive/client/web/web_utils.py \
  scripts/proto/gen_aliases.py scripts/proto/gen_events.py
```

Expected: PASS (`Success: no issues found`).

- [ ] **Step 5: No commit**

Nothing to commit — this task only reverts an unstaged accident. Proceed to Task 2.

---

### Task 2: Restore GitHub Pages (the unblock)

**Files:**
- No repo files. This is a GitHub API configuration change.

**Interfaces:**
- Consumes: nothing.
- Produces: a live site at `https://isaackogan.github.io/TikTokLive/` serving real HTML. Every later task's verification depends on this being true.

Do this **before** the SEO work, against current `master` content. It proves the deploy pipeline works in isolation, so if a later task breaks the site you know the cause is your change and not the pipeline.

- [ ] **Step 1: Confirm the current broken state**

```bash
gh api repos/isaackogan/TikTokLive/pages --jq '{build_type, status, source}'
curl -sS -o /dev/null -w "%{http_code}\n" -L https://isaackogan.github.io/TikTokLive/
```

Expected: `build_type: "legacy"`, and HTTP `404`.

- [ ] **Step 2: Confirm with the maintainer before mutating live config**

This changes a public, live site. Ask explicitly, then proceed. Do not bundle it silently with other work.

- [ ] **Step 3: Flip Pages to workflow mode**

```bash
gh api -X PUT repos/isaackogan/TikTokLive/pages -f build_type=workflow
gh api repos/isaackogan/TikTokLive/pages --jq '{build_type, status}'
```

Expected: `build_type: "workflow"`.

- [ ] **Step 4: Trigger a deploy from master**

```bash
gh workflow run docs.yml --repo isaackogan/TikTokLive --ref master
sleep 30
gh run list --repo isaackogan/TikTokLive --workflow=docs.yml --limit 1
```

Wait for the run to reach `completed / success`.

- [ ] **Step 5: Verify the site is actually alive**

```bash
curl -sS -o /tmp/docs.html -w "status=%{http_code}\n" -L https://isaackogan.github.io/TikTokLive/
grep -oE '<title>[^<]*</title>' /tmp/docs.html
```

Expected: `status=200`, and a real Sphinx title — **not** "Site not found" and not "Page not found". If it still 404s, wait 60s for CDN propagation and retry before investigating further.

- [ ] **Step 6: No commit**

No repo files changed. Record in the PR description that Pages `build_type` was flipped, since it is invisible in the diff.

---

### Task 3: Write the SEO verification script (the failing test)

**Files:**
- Create: `scripts/seo/verify_seo.py`

**Interfaces:**
- Consumes: a built Sphinx HTML tree (default `docs/dist/html`).
- Produces: CLI `python scripts/seo/verify_seo.py [build_dir]`, exit `0` on pass and `1` on failure, printing one line per check. Tasks 4-8 each turn specific checks from FAIL to PASS. Task 11 wires it into `docs.yml`.

This is the plan's test harness. Written first, deliberately failing, so every later task has an objective pass condition.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Assert the SEO invariants of the built documentation.

Run against a built Sphinx HTML tree::

    python scripts/seo/verify_seo.py docs/dist/html

Exits non-zero if any invariant is violated. Wired into docs.yml so an SEO
regression fails the build instead of silently degrading rankings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BASE_URL = "https://isaackogan.github.io/TikTokLive/"
EULER_HOST = "eulerstream.com"

failures: list[str] = []
passes: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (passes if ok else failures).append(name)
    print(f"{'PASS' if ok else 'FAIL'}  {name}{f' :: {detail}' if detail and not ok else ''}")


def main(build_dir: str = "docs/dist/html") -> int:
    root = Path(build_dir)
    if not root.is_dir():
        print(f"FAIL  build directory missing: {root}")
        return 1

    pages = sorted(root.rglob("*.html"))
    index = root / "index.html"

    check("index.html exists", index.is_file())
    if not index.is_file():
        return 1

    index_html = index.read_text(encoding="utf-8", errors="replace")

    # -- Title -------------------------------------------------------------
    title = re.search(r"<title>(.*?)</title>", index_html, re.S)
    title_text = title.group(1).strip() if title else ""
    check("homepage title contains 'TikTok LIVE API'",
          "tiktok live api" in title_text.lower(), title_text)
    check("homepage title has no stale version",
          "6.6.5" not in title_text, title_text)

    # -- Canonical ---------------------------------------------------------
    missing_canonical = [
        p.relative_to(root).as_posix()
        for p in pages
        if 'rel="canonical"' not in p.read_text(encoding="utf-8", errors="replace")
    ]
    check("every page has rel=canonical", not missing_canonical,
          f"{len(missing_canonical)} missing, e.g. {missing_canonical[:3]}")

    check("canonical points at the correct base URL",
          f'rel="canonical" href="{BASE_URL}' in index_html
          or f'href="{BASE_URL}" rel="canonical"' in index_html)

    # -- Open Graph + meta description ------------------------------------
    check("homepage has og:title", 'property="og:title"' in index_html)
    check("homepage has og:description", 'property="og:description"' in index_html)
    check("homepage has og:image", 'property="og:image"' in index_html)
    check("homepage has meta description", 'name="description"' in index_html)

    # -- Sitemap -----------------------------------------------------------
    sitemap = root / "sitemap.xml"
    check("sitemap.xml exists", sitemap.is_file())
    if sitemap.is_file():
        sitemap_xml = sitemap.read_text(encoding="utf-8")
        check("sitemap uses the canonical base URL", BASE_URL in sitemap_xml)
        check("sitemap has no unresolved {lang}/{version} placeholders",
              "{lang}" not in sitemap_xml and "{version}" not in sitemap_xml)
        check("sitemap lists more than one URL", sitemap_xml.count("<loc>") > 1,
              f"{sitemap_xml.count('<loc>')} <loc> entries")

    # -- Dofollow link profile --------------------------------------------
    anchor_re = re.compile(r"<a\b[^>]*>", re.I)
    nofollowed: list[str] = []
    pages_with_euler = 0
    for p in pages:
        html = p.read_text(encoding="utf-8", errors="replace")
        euler_anchors = [a for a in anchor_re.findall(html) if EULER_HOST in a]
        if euler_anchors:
            pages_with_euler += 1
        nofollowed += [
            f"{p.relative_to(root).as_posix()}: {a[:90]}"
            for a in euler_anchors
            if "nofollow" in a.lower()
        ]

    check("no eulerstream.com link is nofollowed", not nofollowed,
          f"{len(nofollowed)} nofollowed, e.g. {nofollowed[:2]}")
    check("eulerstream.com linked from every page",
          pages_with_euler == len(pages),
          f"{pages_with_euler}/{len(pages)} pages")

    # -- Anchor diversity --------------------------------------------------
    anchor_text_re = re.compile(
        r"<a\b[^>]*href=\"[^\"]*" + re.escape(EULER_HOST) + r"[^\"]*\"[^>]*>(.*?)</a>",
        re.I | re.S,
    )
    anchors = {
        re.sub(r"<[^>]+>", "", m).strip().lower()
        for m in anchor_text_re.findall(index_html)
        if re.sub(r"<[^>]+>", "", m).strip()
    }
    check("homepage uses varied anchor text", len(anchors) >= 3,
          f"{len(anchors)} distinct: {sorted(anchors)[:5]}")

    print(f"\n{len(passes)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:2]))
```

- [ ] **Step 2: Build the docs as they are today**

```bash
python -m venv /tmp/seodocs
/tmp/seodocs/bin/pip install -q -e . -r docs/src/requirements.txt
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
```

Expected: build succeeds and `docs/dist/html/index.html` exists.

- [ ] **Step 3: Run the script and verify it FAILS**

```bash
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
```

Expected: `exit=1`. Specifically these must FAIL, since nothing has been implemented yet: title checks, canonical, all four og/meta checks, all sitemap checks, and the "linked from every page" check. This failing output is the task's deliverable — confirm it before moving on.

- [ ] **Step 4: Commit**

```bash
git add scripts/seo/verify_seo.py
git commit -m "test: add SEO invariant verification script for built docs"
```

---

### Task 4: Fix the version source and page titles in conf.py

**Files:**
- Modify: `docs/src/conf.py:1-50`
- Delete: `docs/src/manifest.json`

**Interfaces:**
- Consumes: `TikTokLive/__version__.py`, which defines `PACKAGE_VERSION: str`.
- Produces: module-level `version`, `release`, and `html_baseurl` in `conf.py`. Task 5 reads `html_baseurl` for sitemap and OG config.

- [ ] **Step 1: Replace the manifest-based version block**

In `docs/src/conf.py`, delete `import json` and these two lines:

```python
manifest = json.loads(open("manifest.json", "r").read())
version = "v" + manifest["version"]
```

Replace with:

```python
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
```

- [ ] **Step 2: Set the SEO title and base URL**

Replace this line:

```python
html_title = project + " " + version
```

with:

```python
# The single highest-leverage on-page string on the site. Keyword-led, and
# deliberately free of the version number so the <title> is stable across
# releases (a churning title resets accumulated relevance).
html_title = "TikTok LIVE API for Python — TikTokLive Documentation"
html_short_title = "TikTokLive Docs"

# Required for canonical tags and by sphinx-sitemap. Must match the live
# Pages URL exactly, trailing slash included.
html_baseurl = "https://isaackogan.github.io/TikTokLive/"
```

Also delete the now-misleading `print("Building for version", html_title)` line.

- [ ] **Step 3: Hide the long title in the sidebar**

The sidebar already shows `logo.png`, and the new `html_title` is too long to render there. In `html_theme_options`, add:

```python
    "sidebar_hide_name": True,
```

- [ ] **Step 4: Delete the now-unused manifest**

```bash
git rm docs/src/manifest.json
grep -rn "manifest.json" docs/ scripts/ .github/ || echo "no remaining readers"
```

Expected: `no remaining readers`.

- [ ] **Step 5: Rebuild and verify the title checks now pass**

```bash
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
```

Expected: still `exit=1` overall, but these three now PASS: "homepage title contains 'TikTok LIVE API'", "homepage title has no stale version", and "every page has rel=canonical" (Sphinx emits canonical automatically once `html_baseurl` is set).

- [ ] **Step 6: Commit**

```bash
git add docs/src/conf.py
git commit -m "docs: derive version from __version__.py, add SEO title and baseurl

Kills the stale-title drift at the source: conf.py read manifest.json,
pinned at 6.6.5, so every page rendered 'TikTokLive v6.6.5'."
```

---

### Task 5: Add sitemap and Open Graph extensions

**Files:**
- Modify: `docs/src/requirements.txt`
- Modify: `docs/src/conf.py` (extensions list, new config block)

**Interfaces:**
- Consumes: `html_baseurl` from Task 4.
- Produces: `sitemap.xml` at the build root, plus `og:*`, `twitter:*` and `<meta name="description">` on every page.

- [ ] **Step 1: Add the dependencies**

Append to `docs/src/requirements.txt`:

```
sphinx-sitemap
sphinxext-opengraph
```

Install them:

```bash
/tmp/seodocs/bin/pip install -q sphinx-sitemap sphinxext-opengraph
```

- [ ] **Step 2: Register the extensions**

In `docs/src/conf.py`, add these two entries to the `extensions` list:

```python
    "sphinx_sitemap",
    "sphinxext.opengraph",
```

Note the module names differ in style: underscore for sitemap, dotted for opengraph. Both are correct.

- [ ] **Step 3: Configure them**

Add after the `html_baseurl` line:

```python
# -- Sitemap ----------------------------------------------------------------
# The default scheme is "{lang}{version}{link}", which emits broken URLs when
# neither language nor version dirs are in use. "{link}" is what a flat,
# single-version site needs.
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap.xml"

# -- Open Graph / social cards ----------------------------------------------
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
```

- [ ] **Step 4: Rebuild and verify**

```bash
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
ls -la docs/dist/html/sitemap.xml
head -12 docs/dist/html/sitemap.xml
```

Expected: all four og/meta checks PASS, and all four sitemap checks PASS. The sitemap must contain absolute `https://isaackogan.github.io/TikTokLive/...` URLs with no literal `{lang}` or `{version}`. Still `exit=1` overall — link-profile checks remain.

- [ ] **Step 5: Commit**

```bash
git add docs/src/requirements.txt docs/src/conf.py
git commit -m "docs: add sitemap.xml and Open Graph metadata"
```

---

### Task 6: Give the homepage unique content

**Files:**
- Modify: `docs/src/index.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: a homepage that is no longer a near-duplicate of the GitHub and PyPI renderings of README.md, plus an explicit `<meta name="description">` for the homepage.

The homepage currently `include`s README.md wholesale, making it a near-exact copy of `github.com/isaackogan/TikTokLive` — a far higher-authority page. Google consolidates duplicates toward the strongest copy, which risks discarding the very page whose dofollow links must count. The README include stays (it carries the 7 contextual eulerstream.com links); unique content goes above it.

- [ ] **Step 1: Rewrite index.rst**

Replace the entire contents of `docs/src/index.rst` with:

```rst
.. meta::
   :description: Official documentation for TikTokLive, the unofficial TikTok LIVE API for Python. Connect to any TikTok livestream and receive real-time comments, gifts, likes, follows and viewer counts.
   :keywords: tiktok live api, tiktok api python, tiktoklive, tiktok live chat, tiktok websocket

TikTok LIVE API for Python
==========================

This is the reference documentation for **TikTokLive**, the unofficial
Python client for the TikTok LIVE Webcast service. It connects to any public
TikTok livestream using only a creator's ``@unique_id`` and emits real-time
events for comments, gifts, likes, follows, shares, viewer counts and battles.

These docs cover the full public API surface. If you are new, start with the
quickstart in the project overview below, then move to the module reference.

What is in these docs
---------------------

- :doc:`TikTokLive` — the top-level package: client, events, protobuf schema
- :doc:`TikTokLive.client` — ``TikTokLiveClient``, connection lifecycle, configuration
- :doc:`TikTokLive.client.web` — the HTTP client and its route methods
- :doc:`TikTokLive.client.ws` — the Webcast WebSocket layer
- :doc:`TikTokLive.events` — every event type you can subscribe to
- :doc:`TikTokLive.proto` — generated protobuf message definitions

A note on production use
------------------------

TikTokLive is a reverse-engineering project, not a supported vendor API.
TikTok can and does change the Webcast protocol without notice. For workloads
that need an uptime guarantee, the managed
`TikTok LIVE WebSocket API <https://www.eulerstream.com/websockets>`_ from
`Euler Stream <https://www.eulerstream.com/>`_ handles signing, scaling and
protocol drift for you.

Module reference
----------------

.. toctree::
   :maxdepth: 3

   TikTokLive

Project overview
----------------

.. include:: ../../README.md
   :parser: myst_parser.sphinx_
```

- [ ] **Step 2: Rebuild and verify no build warnings about the toctree**

```bash
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html 2>&1 | tail -20 && cd ../..
```

Expected: build succeeds. Warnings about duplicate labels from the README include are pre-existing and acceptable; a `toctree contains reference to nonexisting document` warning is not — fix the `:doc:` targets against the actual `.rst` filenames in `docs/src/` if one appears.

- [ ] **Step 3: Verify the homepage is no longer a pure duplicate**

```bash
/tmp/seodocs/bin/python - <<'PY'
from pathlib import Path
import re
html = Path("docs/dist/html/index.html").read_text(errors="replace")
body = re.sub(r"<[^>]+>", " ", html)
unique_marker = "This is the reference documentation for"
print("unique intro present:", unique_marker in body)
print("README content still present:", "pip install TikTokLive" in body)
PY
```

Expected: both `True`. Unique content is present *and* the README include still carries its links.

- [ ] **Step 4: Verify anchor diversity now passes**

```bash
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
```

Expected: "homepage uses varied anchor text" PASSes.

- [ ] **Step 5: Commit**

```bash
git add docs/src/index.rst
git commit -m "docs: add unique homepage content above the README include

The homepage was a near-exact duplicate of the GitHub README rendering,
risking consolidation away from the only page whose dofollow links count."
```

---

### Task 7: Add the sitewide dofollow link blocks

**Files:**
- Create: `docs/src/_templates/sidebar/eulerstream.html`
- Create: `docs/src/_templates/page.html`
- Modify: `docs/src/conf.py` (add `html_sidebars`)
- Modify: `docs/src/static/css/custom.css`

**Interfaces:**
- Consumes: Furo's template contract — its default sidebar list from `theme.conf`, and the `{% block footer %}` block in its `page.html`.
- Produces: two dofollow `eulerstream.com` links in the sidebar and one in the footer, on every page of the site.

`templates_path = ['_templates']` is already set in `conf.py`, but the directory does not exist yet. Creating the files below is sufficient.

- [ ] **Step 1: Create the sidebar block**

Create `docs/src/_templates/sidebar/eulerstream.html`:

```html
{#
  Sitewide attribution block. TikTokLive depends on Euler Stream for request
  signing, so this is a genuine dependency disclosure, not an ad.
  Anchor text is deliberately varied across sidebar and footer.
#}
<div class="sidebar-euler">
  <span class="sidebar-euler__label">Production use</span>
  <p class="sidebar-euler__text">
    TikTokLive is a reverse-engineering project. For guaranteed uptime, use the
    managed <a class="sidebar-euler__link"
      href="https://www.eulerstream.com/websockets">TikTok LIVE WebSocket API</a>
    by <a class="sidebar-euler__link"
      href="https://www.eulerstream.com/">Euler Stream</a>.
  </p>
</div>
```

Note: no `rel` attribute at all. Adding `rel="nofollow"` here would defeat the entire purpose and the verification script will fail the build if it appears.

- [ ] **Step 2: Create the footer override**

Create `docs/src/_templates/page.html`:

```html
{#
  Extends Furo's own page.html. The "!" prefix tells Sphinx to load the theme's
  template rather than recursing into this override.
#}
{% extends "!page.html" %}

{% block footer %}
  {{ super() }}
  <div class="euler-footer">
    Request signing and production infrastructure provided by
    <a href="https://www.eulerstream.com/">eulerstream.com</a>.
  </div>
{% endblock footer %}
```

- [ ] **Step 3: Register the sidebar template**

Furo defines its default sidebar list in `theme.conf`. Overriding `html_sidebars` replaces that list wholesale, so all seven defaults must be repeated verbatim or parts of the sidebar will silently vanish. Add to `docs/src/conf.py`:

```python
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
```

- [ ] **Step 4: Style both blocks**

Append to `docs/src/static/css/custom.css`:

```css
.sidebar-euler {
    margin: 1rem var(--sidebar-item-spacing-horizontal, 1rem);
    padding: 0.75rem 0.9rem;
    border: 1px solid var(--color-background-border, #ddd);
    border-radius: 8px;
    background: var(--color-background-secondary, #f8f9fb);
}

.sidebar-euler__label {
    display: block;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-foreground-muted, #6b6b6b);
    margin-bottom: 0.35rem;
}

.sidebar-euler__text {
    margin: 0;
    font-size: 0.8rem;
    line-height: 1.45;
    color: var(--color-foreground-secondary, #4a4a4a);
}

.euler-footer {
    margin-top: 0.75rem;
    font-size: 0.8rem;
    color: var(--color-foreground-muted, #6b6b6b);
}
```

- [ ] **Step 5: Rebuild and verify the link checks pass**

```bash
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
```

Expected: **`exit=0`**. Every check passes, including "no eulerstream.com link is nofollowed" and "eulerstream.com linked from every page".

- [ ] **Step 6: Confirm the sidebar did not lose its navigation**

```bash
grep -c 'sidebar-euler' docs/dist/html/index.html
grep -c 'sidebar-tree\|toctree' docs/dist/html/index.html
```

Expected: both non-zero. If navigation disappeared, an entry was dropped from `html_sidebars` in Step 3.

- [ ] **Step 7: Commit**

```bash
git add docs/src/_templates docs/src/conf.py docs/src/static/css/custom.css
git commit -m "docs: add sitewide Euler Stream attribution blocks

Sidebar and footer dofollow links with varied anchor text. This is the
only surface in the project where we control link markup: PyPI and
GitHub both hard-code rel=nofollow."
```

---

### Task 8: Prepare Search Console verification

**Files:**
- Create: `docs/src/extra/.gitkeep`
- Modify: `docs/src/conf.py` (add `html_extra_path`)

**Interfaces:**
- Consumes: nothing.
- Produces: `html_extra_path = ["extra"]`, so any file dropped in `docs/src/extra/` is copied verbatim to the site root. This is the mechanism for the Google verification file; the token itself is external input the maintainer supplies.

- [ ] **Step 1: Create the passthrough directory**

```bash
mkdir -p docs/src/extra && touch docs/src/extra/.gitkeep
```

- [ ] **Step 2: Register it in conf.py**

Add near `html_static_path`:

```python
# Files copied verbatim to the site root. Used for the Google Search Console
# verification file, which must be served at an exact path.
html_extra_path = ["extra"]
```

- [ ] **Step 3: Verify the passthrough works**

```bash
echo "seo-passthrough-probe" > docs/src/extra/probe.txt
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
cat docs/dist/html/probe.txt
rm docs/src/extra/probe.txt
```

Expected: prints `seo-passthrough-probe`, proving files land at the site root.

- [ ] **Step 4: Commit**

```bash
git add docs/src/extra/.gitkeep docs/src/conf.py
git commit -m "docs: add extra/ passthrough for Search Console verification"
```

- [ ] **Step 5: Hand off the maintainer-only steps**

The token requires a Google login and cannot be automated. Give the maintainer these exact instructions:

1. Open Search Console and add a **URL prefix** property for `https://isaackogan.github.io/TikTokLive/`.
2. Choose the **HTML file** verification method and download `googleXXXXXXXX.html`.
3. Run:

```bash
cp ~/Downloads/google*.html docs/src/extra/
git add docs/src/extra/ && git commit -m "docs: add Search Console verification file"
```

4. After the next deploy, click Verify, then submit `https://isaackogan.github.io/TikTokLive/sitemap.xml` under Sitemaps.

Note the property must be the `/TikTokLive/` **URL prefix**, not the bare domain. `isaackogan.github.io` is a Public Suffix List entry, so a domain-level property is not available to you and would cover other users' sites in any case.

---

### Task 9: Improve PyPI packaging metadata

**Files:**
- Modify: `pyproject.toml` (`[project].description`, `[project].classifiers`, `[project.urls]`)

**Interfaces:**
- Consumes: nothing.
- Produces: the metadata mirrored verbatim by libraries.io, Snyk Advisor, deps.dev and piwheels — separately indexed surfaces. Task 12 publishes it.

These links are `rel="nofollow"` on PyPI itself, so this earns no DR directly. It is worth doing for the mirror surfaces, for click-through traffic, and because `Homepage` currently points at a stale URL.

**Do not touch the license classifier in this task.** Task 10 owns that and is blocked.

- [ ] **Step 1: Rewrite the summary**

`description` is the meta description on every mirror site. Replace:

```toml
description = "TikTok Live Python Client"
```

with:

```toml
description = "Unofficial TikTok LIVE API for Python: real-time chat, gift, like, follow and viewer events from any TikTok livestream."
```

- [ ] **Step 2: Expand project URLs**

Replace the entire `[project.urls]` section:

```toml
[project.urls]
Homepage = "https://github.com/isaackogan/TikTokLive"
Documentation = "https://isaackogan.github.io/TikTokLive/"
Source = "https://github.com/isaackogan/TikTokLive"
Issues = "https://github.com/isaackogan/TikTokLive/issues"
Changelog = "https://github.com/isaackogan/TikTokLive/releases"
Discord = "https://discord.gg/e2XwPNTBBr"
"Production API" = "https://www.eulerstream.com/"
```

- [ ] **Step 3: Fix the classifiers**

`Topic :: Software Development :: Build Tools` is inaccurate — this is not a build tool. Replace the non-license classifier entries with:

```toml
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Framework :: AsyncIO",
    "Topic :: Communications :: Chat",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Multimedia :: Video",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
```

The `License ::` line is carried over unchanged **on purpose** — Task 10 corrects it once the maintainer decides the wording. `Development Status` moves to Production/Stable because Task 12 ships a 7.0.0 stable release.

- [ ] **Step 4: Verify the metadata builds and reads back correctly**

```bash
/tmp/seodocs/bin/pip install -q build
/tmp/seodocs/bin/python -m build --wheel --outdir /tmp/seobuild . >/dev/null 2>&1
/tmp/seodocs/bin/python - <<'PY'
import zipfile, glob, email
whl = sorted(glob.glob("/tmp/seobuild/*.whl"))[-1]
with zipfile.ZipFile(whl) as z:
    meta = next(n for n in z.namelist() if n.endswith("METADATA"))
    msg = email.message_from_string(z.read(meta).decode())
print("Summary:", msg["Summary"])
for u in msg.get_all("Project-URL") or []:
    print("Project-URL:", u)
PY
```

Expected: the new summary, and seven `Project-URL` entries including `Documentation` and `Production API`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "build: expand PyPI project URLs, summary and classifiers"
```

---

### Task 10: Reconcile the license declaration — BLOCKED

**Files:**
- Modify: `pyproject.toml` (`[project].license`, the `License ::` classifier)

**Interfaces:**
- Consumes: Task 9's classifier list.
- Produces: one internally consistent license declaration.

> **BLOCKED: do not implement without an explicit maintainer decision.**
> This is a legal determination, not an SEO one. It does not block any other
> task — skip to Task 11 and return here once the answer arrives.

The project currently states its license three incompatible ways:

| Location | Value |
|---|---|
| `pyproject.toml` classifier | `License :: OSI Approved :: MIT License` |
| `pyproject.toml` `license` field | `AGPL` |
| `README.md` | "modified AGPL" |

"Modified AGPL" has no valid SPDX identifier, so the classifier cannot express it. Once the maintainer picks one of these, apply the matching edit:

- [ ] **Step 1: Apply the maintainer's chosen option**

**Option A — modified AGPL (matches README and the LICENSE file):**

```toml
license = { file = "LICENSE" }
```

and in `classifiers`, replace the MIT line with:

```toml
    "License :: Other/Proprietary License",
```

**Option B — unmodified AGPL-3.0-or-later:**

```toml
license = "AGPL-3.0-or-later"
```

and in `classifiers`, replace the MIT line with:

```toml
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
```

**Option C — genuinely MIT:** leave `classifiers` unchanged, set `license = "MIT"`, and update `README.md` and the `LICENSE` file to match. Only valid if the AGPL wording was the mistake.

- [ ] **Step 2: Verify consistency**

```bash
grep -n 'license' pyproject.toml
grep -n 'License ::' pyproject.toml
grep -n -i 'licensed under' README.md
```

Expected: all three describe the same license. If `[tool.setuptools] license-files` conflicts with a `license = { file = ... }` value, remove the redundant `license-files` entry.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: reconcile license declaration across metadata"
```

---

### Task 11: Gate the build on SEO, then deploy to production

**Files:**
- Modify: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: `scripts/seo/verify_seo.py` from Task 3.
- Produces: a live, fully optimized site at `https://isaackogan.github.io/TikTokLive/`, with SEO regressions failing CI from now on.

- [ ] **Step 1: Add the verification gate**

In `.github/workflows/docs.yml`, insert between the `Build HTML` step and the `Add .nojekyll` step:

```yaml
      - name: Verify SEO invariants
        run: python scripts/seo/verify_seo.py docs/dist/html
```

Placed after the build and before upload, so a regression fails the run and never reaches the live site.

- [ ] **Step 2: Confirm the whole suite is still green locally**

```bash
python -m pytest -q
cd docs/src && /tmp/seodocs/bin/python -m sphinx -b html . ../dist/html && cd ../..
/tmp/seodocs/bin/python scripts/seo/verify_seo.py docs/dist/html; echo "exit=$?"
```

Expected: tests pass, `exit=0`.

- [ ] **Step 3: Commit and open the PR**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: fail the docs build on SEO regressions"
git push -u origin seo/backlink-optimization
gh pr create --title "SEO: restore docs site and add backlink optimization" \
  --body "Implements docs/superpowers/specs/2026-08-17-seo-backlink-design.md

Note: GitHub Pages build_type was flipped from 'legacy' to 'workflow' via the
API. That change is invisible in this diff but was required — the Actions
deploy had been running successfully and being ignored since 0f87ab1."
```

- [ ] **Step 4: Merge after review, then confirm the deploy**

```bash
gh pr merge --squash
sleep 45
gh run list --repo isaackogan/TikTokLive --workflow=docs.yml --limit 1
```

Wait for `completed / success`. The "Verify SEO invariants" step must pass in CI, not just locally.

- [ ] **Step 5: Verify against the live site, not the local build**

```bash
curl -sS -o /tmp/live.html -w "index=%{http_code}\n" -L https://isaackogan.github.io/TikTokLive/
curl -sS -o /tmp/live_sitemap.xml -w "sitemap=%{http_code}\n" -L https://isaackogan.github.io/TikTokLive/sitemap.xml
grep -oE '<title>[^<]*</title>' /tmp/live.html
grep -oE '<link rel="canonical" href="[^"]*"' /tmp/live.html
grep -c 'eulerstream' /tmp/live.html
grep -oE '<a[^>]*eulerstream[^>]*nofollow[^>]*>' /tmp/live.html || echo "no nofollowed euler links (correct)"
```

Expected: `index=200`, `sitemap=200`, keyword title, canonical present, non-zero eulerstream count, and `no nofollowed euler links (correct)`.

---

### Task 12: Release 7.0.0 to PyPI

**Files:**
- No manual edits. `release.yml` stamps `pyproject.toml` and `TikTokLive/__version__.py`.

**Interfaces:**
- Consumes: everything merged in Task 11.
- Produces: `pypi.org/project/TikTokLive/` serving 7.0.0 with the rewritten README and the new metadata.

`release.yml` refuses to run from any branch but `master`, so Task 11 must be merged first.

- [ ] **Step 1: Confirm you are releasing from a green master**

```bash
git checkout master && git pull
git log --oneline -3
gh run list --repo isaackogan/TikTokLive --workflow=test.yml --limit 1
gh run list --repo isaackogan/TikTokLive --workflow=lint.yml --limit 1
```

Expected: both `success`. Do not proceed otherwise.

- [ ] **Step 2: Confirm the maintainer still wants 7.0.0 stable**

The current version is `7.0.0b2`. Promoting to `7.0.0` declares the 7.x API stable. This was reaffirmed during planning, but confirm once more at the point of no return — a published PyPI version cannot be replaced, only yanked.

- [ ] **Step 3: Dispatch the release**

```bash
gh workflow run release.yml --repo isaackogan/TikTokLive -f version=7.0.0
sleep 30
gh run list --repo isaackogan/TikTokLive --workflow=release.yml --limit 1
```

Wait for `completed / success`.

- [ ] **Step 4: Verify PyPI actually served the new metadata**

```bash
sleep 60
curl -sS https://pypi.org/pypi/TikTokLive/json | python3 -c "
import json,sys
d = json.load(sys.stdin)['info']
print('version :', d['version'])
print('summary :', d['summary'])
for k, v in (d.get('project_urls') or {}).items():
    print(f'url     : {k} -> {v}')
desc = d.get('description') or ''
print('README is the rewritten one:',
      'TikTokLive is the definitive third-party Python library' in desc)
"
```

Expected: `version: 7.0.0`, the new summary, seven project URLs, and `True` for the README check. That `True` is the whole point of this task — it means `pypi.org/project/TikTokLive/` now serves the rewritten README instead of the 6.6.6 text.

- [ ] **Step 5: Merge the version-bump PR**

`release.yml` opens a PR titled `chore: release v7.0.0`. Merge it so `master` matches what was published — otherwise the docs site keeps rendering the old version, since `conf.py` reads `TikTokLive/__version__.py`.

```bash
gh pr list --repo isaackogan/TikTokLive --search "chore: release v7.0.0"
gh pr merge <number> --squash
```

- [ ] **Step 6: Confirm the docs picked up the new version**

```bash
sleep 60
curl -sS -L https://isaackogan.github.io/TikTokLive/ | grep -oE 'v?7\.0\.0' | head -3
```

Expected: `7.0.0` appears. The `<title>` must **not** change — it is version-free by design (Task 4).

---

## Post-Implementation Handoff

Maintainer-only, cannot be automated:

1. **Search Console** — complete Task 8 Step 5: verify the property, submit the sitemap.
2. **Request indexing** for `https://isaackogan.github.io/TikTokLive/` via the URL Inspection tool to accelerate recovery of the four-month outage.
3. **Watch for recovery** over 2-4 weeks. The URL was restored exactly, with no redirect hop, so recovery should be substantially complete rather than partial.

Deliberately deferred, per the spec's non-goals:

- Hand-written guide pages (quickstart, gift handling, deployment, FAQ) — revisit once the site is confirmed indexing.
- A purpose-built 1200x630 OG card. `SquareLogo.png` at 1080x1080 works but is not the ideal aspect ratio.
- An `isaackogan.github.io` user-site repo to own a root `robots.txt`. Optional upside; not required, since discovery comes from the sitemap.
