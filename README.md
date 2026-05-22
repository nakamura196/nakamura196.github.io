# nakamura196.github.io

Personal academic website of **Satoru Nakamura** (中村 覚) — Associate Professor,
Historiographical Institute, The University of Tokyo.

Live at <https://nakamura196.github.io/>. Built with the
[Academic Pages](https://github.com/academicpages/academicpages.github.io)
(Jekyll) template and hosted on GitHub Pages.

## Content is generated automatically

Most pages are **not** hand-written — they are generated from external sources,
so the site stays in sync as new work is added:

| Page | Source | Generator |
|------|--------|-----------|
| Publications, Talks, CV | [researchmap](https://researchmap.jp/nakamura.satoru) API | `scripts/build_from_researchmap.py` |
| Software | [GitHub](https://github.com/nakamura196) API | `scripts/build_github_portfolio.py` |

A scheduled GitHub Actions workflow (`.github/workflows/update.yml`) re-runs both
generators **weekly**, commits any changes, and triggers a Pages rebuild — no
local setup required. You can also run it on demand from the Actions tab
("Run workflow").

### Regenerate locally

```sh
python3 scripts/build_from_researchmap.py     # publications / talks / CV
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

To change publications/talks/CV/software, edit the source on researchmap or
GitHub and re-run the generators (the workflow does this automatically).

---

Template: Academic Pages, forked from the Minimal Mistakes theme (© Michael Rose, MIT). See `LICENSE`.
