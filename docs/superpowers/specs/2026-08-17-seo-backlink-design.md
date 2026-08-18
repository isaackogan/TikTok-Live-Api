# SEO & Backlink Design: TikTokLive as an Authority Source for eulerstream.com

**Date:** 2026-08-17
**Status:** Approved, pending implementation plan
**Repo:** `isaackogan/TikTokLive`

## 1. Problem

The TikTokLive project should act as a strong third-party backlink source for
`www.eulerstream.com`. It currently passes **zero** link equity, and its only
capable surface has been offline for roughly four months.

## 2. Verified findings

These were confirmed against live systems and upstream source, not assumed.

### 2.1 The documentation site is dead

`https://isaackogan.github.io/TikTokLive/` returns **404 "Site not found"**.

Root cause: commit `0f87ab1` (2026-04-28, *"move docs to docs/src, build via
GitHub Actions"*) deleted the 52 built HTML files that legacy GitHub Pages had
been serving from `master:/docs` — including three `index.html` — and switched
to an Actions-based build. GitHub Pages was never switched out of legacy mode.

Current Pages config:

```
build_type: "legacy"
source:     { branch: "master", path: "/docs" }
status:     "errored"
```

`docs.yml` builds correctly and `actions/deploy-pages@v4` creates deployments,
but legacy mode ignores them and serves raw source instead. Confirmed:
`/TikTokLive/src/conf.py` returns **200** while every HTML path returns 404.

The site has been down since **2026-04-28**. The repo rename to
`TikTok-Live-Api` (since reverted) was a separate, smaller issue and was *not*
the cause.

### 2.2 PyPI and GitHub pass no link equity

| Surface | Verdict | Evidence |
|---|---|---|
| PyPI description body | `nofollow` | `readme_renderer/clean.py` calls `nh3.clean(..., link_rel="nofollow")` |
| PyPI sidebar project links | `nofollow` | `warehouse/templates/includes/packaging/metadata/project-links.html:71,85` |
| GitHub README | `nofollow` | all 6 eulerstream.com anchors on the repo page |
| GitHub sidebar Website | `nofollow` | `rel="noopener noreferrer nofollow"` |

### 2.3 Consequence

The GitHub Pages docs site is the **only** surface in this project where we
control link markup and can emit dofollow links. `docs/src/index.rst` includes
the README, so its 7 contextual eulerstream.com links render there as followed
links on a third-party domain. That surface is at zero percent uptime.

Caveat: `github.io` is on the Public Suffix List, so `isaackogan.github.io` is
scored as its own site and inherits nothing from `github.com`. Its authority is
its own — real, but not DR90.

### 2.4 Secondary defects

- PyPI serves the **pre-rewrite README**. Latest stable is `6.6.6`
  (2026-07-21); `7.0.0b2` is a prerelease and does not take the project page.
- `project_urls` contains only `Homepage`, pointing at the stale repo name.
- License is stated three different ways: classifier `MIT`, `license` field
  `AGPL`, README "modified AGPL".
- `conf.py` has no `html_baseurl`, sitemap, OG tags, or meta descriptions.
- `manifest.json` is pinned at `6.6.5`, so the docs title renders
  `TikTokLive v6.6.5`.
- A stray `2` is appended at module level to
  `TikTokLive/client/web/routes/fetch_signed_websocket.py` (uncommitted).

## 3. Goals and non-goals

**Goals**

1. Restore the docs site at its indexed canonical URL.
2. Make it fully indexable (canonical, sitemap, OG, meta descriptions, titles).
3. Emit a moderate, natural dofollow link profile to eulerstream.com.
4. Publish the rewritten README to PyPI via a 7.0.0 stable release.
5. Correct packaging metadata for the aggregator surfaces that mirror it.

**Non-goals**

- Ranking the GitHub repo for "tiktok live api". `eulerstream.com` already
  holds position #1 for that term; a competing repo listing is at best a second
  slot and at worst self-cannibalisation.
- Renaming the PyPI package. It would break `pip install TikTokLive`, reset
  download statistics, and orphan indexed version URLs, for zero equity gain.
- Moving docs onto a `eulerstream.com` subdomain. That would convert the only
  third-party backlink source into an internal link.
- New hand-written guide content. Deferred to a follow-up.

## 4. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Release vehicle | **Cut 7.0.0 stable** | Publishes the README and yields a major-version event that aggregators pick up |
| Link profile | **Moderate** | README links plus a sitewide sidebar/footer block; avoids the sitewide exact-match-anchor footprint |
| Docs depth | **Optimise existing** | Prove the pipeline is live and indexing before investing in content |
| SEO mechanism | **Sphinx extensions + Furo template overrides** | Declarative, colocated in `conf.py`, survives theme upgrades |

Rejected alternative for the mechanism: a post-build script rewriting
`docs/dist/html`. No new dependencies and total control, but it is a second
source of truth that breaks silently the first time Furo changes its markup.

## 5. Design

### 5.1 Resurrect Pages

Everything downstream is inert until this is true.

```
PUT /repos/isaackogan/TikTokLive/pages   { "build_type": "workflow" }
```

`docs.yml` already builds to `docs/dist/html` and uploads via
`actions/deploy-pages@v4`; no workflow change is required. Reversible. Because
it is an outward-facing change to a live repo, it is confirmed at execution
time rather than applied silently.

Then re-run `docs.yml` and verify real HTML is served at `/TikTokLive/`.

### 5.2 On-page SEO in `conf.py`

- `html_baseurl = "https://isaackogan.github.io/TikTokLive/"` — emits canonical
  tags and is a hard prerequisite for `sphinx-sitemap`.
- Add `sphinx_sitemap` (2.9.0) with `sitemap_url_scheme = "{link}"`. The
  default scheme is `{lang}{version}{link}`, which produces wrong URLs when
  neither is set.
- Add `sphinxext.opengraph` (0.13.0) for OG and Twitter cards. Use
  `.github/SquareLogo.png` (1080x1080) as the OG image; a purpose-built
  1200x630 card is a follow-up, not a blocker.
- `html_title` becomes keyword-led:
  `TikTok LIVE API for Python — TikTokLive Documentation`. This is the
  highest-leverage string on the site and is currently both keyword-free and
  stale.
- Read the version from `TikTokLive/__version__.py` — the file `release.yml`
  already stamps — instead of `manifest.json`. Delete `manifest.json`;
  `conf.py:17` is its only reader. This makes the stale-title drift
  structurally impossible rather than merely fixed.
- Add a Search Console verification file via `html_extra_path`.

**Constraint: robots.txt is not achievable and is not needed.** Project Pages
sites serve under `/TikTokLive/`, but crawlers honour robots.txt only at the
domain root, which only a repo named `isaackogan.github.io` can own; it does
not exist. robots.txt is an exclusion mechanism and the goal here is inclusion.
Discovery comes from the sitemap submitted directly in Search Console.
Creating the user-site repo is optional upside, not a dependency.

### 5.3 Resolve the duplicate-content trap

`index.rst` includes the README wholesale, making the docs homepage a near-copy
of `github.com/isaackogan/TikTokLive` (much higher authority) and of the PyPI
description. Google consolidates duplicates toward the strongest copy, so the
docs homepage risks being discarded as redundant — and it is precisely the page
whose dofollow links must count.

Fix: retain the README include, which carries the 7 contextual eulerstream.com
links, but prepend 200-300 words of unique, docs-specific content above it —
orientation, what the documentation covers, where to start.

### 5.4 Link profile (moderate)

| Placement | Renders on | Anchor |
|---|---|---|
| README contextual links | homepage | existing, varied |
| Furo sidebar attribution block | all ~9 pages | "Euler Stream" |
| Footer line | all ~9 pages | rotated: "TikTok LIVE API", "WebSocket API", bare domain |

Approximately 25 dofollow links from a third-party domain, against zero today.
Anchor text is varied deliberately: a single exact-match anchor repeated
sitewide is the footprint most likely to be discounted.

### 5.5 Packaging metadata

Nofollow, so this earns no DR directly. It is worth doing because the summary
and project links are mirrored verbatim by libraries.io, Snyk Advisor,
deps.dev and piwheels, which are separately indexed surfaces.

- `project_urls`: add Documentation, Source, Issues, Changelog, and a Euler
  Stream entry.
- Rewrite `description`; `"TikTok Live Python Client"` currently serves as the
  meta description on every mirror.
- Add the Python 3.13 classifier and richer `Topic ::` entries.
- **License reconciliation is a legal decision, not an SEO one.** Proposal:
  drop the incorrect `MIT` classifier and point `license` at the LICENSE file.
  Requires explicit maintainer sign-off on wording before implementation.

### 5.6 Release 7.0.0 stable

1. Revert the stray `2` in `fetch_signed_websocket.py`.
2. Run tests and mypy.
3. Dispatch `release.yml` with version `7.0.0`.

Whether 7.0.0 is stable-ready is the maintainer's call; anything encountered
that suggests otherwise is surfaced rather than worked around.

## 6. Verification

No step is considered done without the corresponding evidence.

| Check | Passing condition |
|---|---|
| Docs URL | `200` and a keyword title, not "Site not found" |
| `sitemap.xml` | `200`, lists all pages |
| Built HTML | canonical and OG tags present |
| eulerstream links | **no** `rel="nofollow"` in built HTML |
| PyPI JSON | `7.0.0`, new `project_urls`, new summary |
| Tests / mypy | pass before release dispatch |

**Out of scope for automation:** Search Console verification and sitemap
submission require maintainer login. The verification file is generated and
served via `html_extra_path`; the submission steps are handed over.

## 7. Risks

| Risk | Mitigation |
|---|---|
| 7.0.0 is not actually stable-ready | Tests and mypy gate the release; concerns surfaced, not worked around |
| Pages flip affects a live site | Single reversible config field; confirmed at execution |
| Sitewide links read as manipulative | Moderate tier with varied anchors; no exact-match repetition |
| Docs homepage still loses the duplicate contest | Unique prepended content; re-verify indexing after deploy |
| Recovery of the old URL's equity is partial | URL restored exactly, so no redirect hop; monitor in Search Console |
