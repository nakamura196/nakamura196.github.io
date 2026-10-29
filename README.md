# nakamura196.github.io

Personal academic website of **Satoru Nakamura** (中村 覚) — Associate Professor,
The University of Tokyo.

Live at <https://nakamura196.github.io/>. Built with the
[Academic Pages](https://github.com/academicpages/academicpages.github.io)
(Jekyll) template and hosted on GitHub Pages.

## Content is generated automatically

Most pages are **not** hand-written — they are generated from external sources,
so the site stays in sync as new work is added:

| Page | Source | Generator |
|------|--------|-----------|
| Publications, Talks, CV, Works, Grants | `master/` (see below) | `scripts/build_site.py` |
| Software | [GitHub](https://github.com/nakamura196) API | `scripts/build_github_portfolio.py` |

A scheduled GitHub Actions workflow (`.github/workflows/update.yml`) re-runs both
generators **daily**, commits any changes, and triggers a Pages rebuild — no
local setup required. You can also run it on demand from the Actions tab
("Run workflow").

### Regenerate locally

```sh
python3 scripts/build_site.py                 # publications / talks / CV from master/
GH_TOKEN=$(gh auth token) python3 scripts/build_github_portfolio.py  # software
```

### Preview locally (Docker)

The system Ruby is too old for Jekyll, so preview via Docker:

```sh
docker compose up -d     # serves http://localhost:4000/
docker compose down      # stop
```

GitHub Pages builds the published site server-side, so neither Docker nor a
local Ruby is needed to deploy — just push to `master`.

## Editing

- Bio / homepage: `_pages/about.md`
- Profile, links, site title: `_config.yml` (the `author:` block)
- Navigation: `_data/navigation.yml`

To change publications/talks/CV, edit `master/` (below) and run
`scripts/build_site.py`. Software comes from GitHub (the workflow re-runs it).

## master/ — the source of truth for achievements

`master/<kind>.json` holds the items exactly in researchmap API format
(`books_etc`, `published_papers`, `misc`, `presentations`, `works`,
`research_projects`, `awards`, ...), and `master/profile.json` the profile.
The site is built from these files. researchmap is updated from the master,
not the other way round. `master/` is excluded from the published site.

- Fields starting with `x-` are local-only and never sent to researchmap
  (`x-thumbnail`, `x-thumbnail-source`, `x-en-source` = where an English fill-in came from).
- English fill-ins for Japanese-only records are written into the item
  (`item[field].en`) with the source URL in `x-en-source[field]`.
- Add an item: append an object to the right file, in the same shape as its
  neighbours. For something researchmap does not have (e.g. a grant not on
  researchmap), add it to `master/research_projects.json` **without `rm:id`**.
  It is then listed by `rm_diff.py` / `export_researchmap.py` as "master only".
- Then run `python3 scripts/build_site.py`.

Scripts:

| Command | What it does |
|---|---|
| `python3 scripts/build_site.py` | master -> `_publications/`, `_talks/`, `_data/cv*.json`, `_data/researchmap.json` |
| `python3 scripts/rm_diff.py` | Markdown report of differences from the live researchmap API (read-only). The daily workflow files it as one issue |
| `python3 scripts/export_researchmap.py` | Writes `build/researchmap-import.jsonl` (items without `rm:id` and items that differ; `x-` removed). The wrapper format is unverified: check researchmap's import spec before uploading |
| `python3 scripts/fetch_work_thumbnails.py` | Fills missing `images/works/<rm:id>.jpg` (ldas.jp works list, then og:image, then a headless-Chrome screenshot). Needs macOS `sips`. Never overwrites existing images |
| `python3 scripts/rm_export_to_master.py [--force]` | Re-seeds master/ from the API. Skips existing files unless `--force` (which discards local edits) |

---

Template: Academic Pages, forked from the Minimal Mistakes theme (© Michael Rose, MIT). See `LICENSE`.
