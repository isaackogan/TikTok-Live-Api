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

    # -- Navigation integrity ---------------------------------------------
    # conf.py overrides html_sidebars to inject the attribution block, and
    # overriding replaces Furo's entire default list. A dropped entry, or a
    # future Furo release renaming a template, would silently delete site
    # navigation while every SEO check above still passed. Furo is unpinned,
    # so fail loudly rather than ship a site nobody can navigate.
    missing_nav = [
        p.relative_to(root).as_posix()
        for p in pages
        if "sidebar-tree" not in p.read_text(encoding="utf-8", errors="replace")
    ]
    check("every page retains sidebar navigation", not missing_nav,
          f"{len(missing_nav)} missing, e.g. {missing_nav[:3]}")

    print(f"\n{len(passes)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:2]))
