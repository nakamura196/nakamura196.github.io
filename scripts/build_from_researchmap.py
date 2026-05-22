#!/usr/bin/env python3
"""Generate academicpages content from a researchmap profile.

Pulls achievements from the researchmap public API and writes:
  - _publications/*.md   (books, journal/proceedings papers, misc articles)
  - _talks/*.md          (presentations)
  - _data/cv.json        (jsonresume: basics, work, education, awards,
                          research grants, committee memberships)

Re-runnable: regenerates the above from scratch on every run, so adding a
publication on researchmap and re-running keeps the site in sync. Hand edits
to generated files are intentionally overwritten — edit researchmap instead.

Usage:
    python3 scripts/build_from_researchmap.py            # uses PERMALINK below
    PERMALINK=nakamura.satoru python3 scripts/build_from_researchmap.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

PERMALINK = os.environ.get("PERMALINK", "nakamura.satoru")
API = "https://api.researchmap.jp"
ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "rm_cache"

# --- static profile bits not in researchmap (edit here) ---
PROFILE = {
    "name": "Satoru Nakamura",
    "email": "",
    "website": "https://nakamura196.github.io",
    "orcid": "https://orcid.org/0000-0001-8245-7925",
    "github": "nakamura196",
    "googlescholar": "https://scholar.google.com/citations?user=gbuswBEAAAAJ",
}


def fetch(kind: str) -> list[dict]:
    """Fetch all items of one achievement type (cached to disk)."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"{kind}.json"
    url = f"{API}/{PERMALINK}/{kind}?limit=2000"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    except Exception as e:  # fall back to cache if network fails
        if cache_file.exists():
            print(f"  ! {kind}: network failed ({e}); using cache")
            data = json.loads(cache_file.read_text())
        else:
            print(f"  ! {kind}: unavailable ({e})")
            return []
    if not isinstance(data, dict):
        return []
    return data.get("items", []) or []


def lang(field, prefer="en"):
    """Pick a language value from a {ja,en} dict; fall back to the other."""
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        for key in ([prefer, "en", "ja"] if prefer == "en" else [prefer, "ja", "en"]):
            v = field.get(key)
            if v:
                return v
    return ""


def names(field):
    """Join an author/presenter list (prefer en list) into 'A, B, C'."""
    if not isinstance(field, dict):
        return ""
    lst = field.get("en") or field.get("ja") or []
    return ", ".join(n.get("name", "") for n in lst if n.get("name"))


def full_date(d: str | None) -> str:
    """Normalize 'YYYY' / 'YYYY-MM' / 'YYYY-MM-DD' to a sortable YYYY-MM-DD."""
    if not d:
        return "1900-01-01"
    parts = str(d).split("-")
    while len(parts) < 3:
        parts.append("01")
    y, m, day = parts[0], parts[1] or "01", parts[2] or "01"
    return f"{y}-{int(m):02d}-{int(day):02d}"


def y(s: str) -> str:
    return full_date(s)[:4]


def doi_url(identifiers: dict) -> str:
    if not isinstance(identifiers, dict):
        return ""
    doi = identifiers.get("doi")
    if isinstance(doi, list) and doi:
        return f"https://doi.org/{doi[0]}"
    return ""


def yaml_str(s: str) -> str:
    """Quote a scalar safely for YAML (JSON double-quoted form is valid YAML)."""
    return json.dumps(s, ensure_ascii=False)


def write_md(path: Path, front: dict, body: str = ""):
    lines = ["---"]
    for k, v in front.items():
        if v is None or v == "":
            continue
        lines.append(f"{k}: {yaml_str(v) if isinstance(v, str) else v}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_dir(rel: str, keep_dotfiles=True):
    d = ROOT / rel
    d.mkdir(exist_ok=True)
    for f in d.glob("*.md"):
        if keep_dotfiles and f.name.startswith("."):
            continue
        f.unlink()


# --------------------------------------------------------------------------
# Publications: books_etc / published_papers / misc
# --------------------------------------------------------------------------
def gen_publications():
    clean_dir("_publications")
    out = ROOT / "_publications"
    n = 0

    for it in fetch("books_etc"):
        rid = it.get("rm:id", str(n))
        date = full_date(it.get("publication_date"))
        title = lang(it.get("book_title")) or "(untitled)"
        venue = lang(it.get("publisher"))
        cite = f'{names(it.get("authors"))} ({y(date)}). <i>{title}</i>. {venue}.'
        write_md(out / f"{date}-book-{rid}.md", {
            "title": title,
            "collection": "publications",
            "category": "books",
            "permalink": f"/publication/{date}-book-{rid}",
            "date": date,
            "venue": venue,
            "paperurl": doi_url(it.get("identifiers", {})),
            "citation": cite,
        })
        n += 1

    for it in fetch("published_papers"):
        rid = it.get("rm:id", str(n))
        date = full_date(it.get("publication_date"))
        title = lang(it.get("paper_title")) or "(untitled)"
        venue = lang(it.get("publication_name"))
        vol = it.get("volume", "")
        pages = ""
        if it.get("starting_page"):
            pages = it.get("starting_page", "")
            if it.get("ending_page"):
                pages += f'-{it.get("ending_page")}'
        bits = f'{names(it.get("authors"))} ({y(date)}). &quot;{title}.&quot; <i>{venue}</i>'
        if vol:
            bits += f", {vol}"
        if pages:
            bits += f", {pages}"
        bits += "."
        if it.get("referee"):
            bits += " [refereed]"
        write_md(out / f"{date}-paper-{rid}.md", {
            "title": title,
            "collection": "publications",
            "category": "manuscripts",
            "permalink": f"/publication/{date}-paper-{rid}",
            "date": date,
            "venue": venue,
            "paperurl": doi_url(it.get("identifiers", {})),
            "citation": bits,
        })
        n += 1

    for it in fetch("misc"):
        rid = it.get("rm:id", str(n))
        date = full_date(it.get("publication_date"))
        title = lang(it.get("paper_title")) or "(untitled)"
        venue = lang(it.get("publication_name"))
        cite = f'{names(it.get("authors"))} ({y(date)}). &quot;{title}.&quot; <i>{venue}</i>.'
        write_md(out / f"{date}-misc-{rid}.md", {
            "title": title,
            "collection": "publications",
            "category": "misc",
            "permalink": f"/publication/{date}-misc-{rid}",
            "date": date,
            "venue": venue,
            "citation": cite,
        })
        n += 1
    print(f"  _publications: {n} files")


# --------------------------------------------------------------------------
# Talks: presentations
# --------------------------------------------------------------------------
def gen_talks():
    clean_dir("_talks")
    out = ROOT / "_talks"
    n = 0
    for it in fetch("presentations"):
        rid = it.get("rm:id", str(n))
        date = full_date(it.get("publication_date") or it.get("from_event_date"))
        title = lang(it.get("presentation_title")) or "(untitled)"
        venue = lang(it.get("event"))
        raw = (lang(it.get("presentation_type")) or "talk").lower()
        ptype = {
            "oral_presentation": "Oral presentation",
            "poster_presentation": "Poster",
            "public_symposium": "Symposium",
            "nominated_symposium": "Symposium",
            "keynote_oral_presentation": "Keynote",
            "invited_oral_presentation": "Invited talk",
        }.get(raw, raw.replace("_", " ").capitalize())
        intl = it.get("is_international_presentation")
        loc = "International" if intl else "Japan"
        if it.get("invited") and "nvited" not in ptype and "eynote" not in ptype:
            ptype = f"Invited {ptype.lower()}"
        write_md(out / f"{date}-talk-{rid}.md", {
            "title": title,
            "collection": "talks",
            "type": ptype,
            "permalink": f"/talks/{date}-talk-{rid}",
            "venue": venue,
            "date": date,
            "location": loc,
        })
        n += 1
    print(f"  _talks: {n} files")


# --------------------------------------------------------------------------
# CV (jsonresume) : basics, work, education, awards, projects, volunteer
# --------------------------------------------------------------------------
def gen_cv():
    work = []
    for it in sorted(fetch("research_experience"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        end = it.get("to_date", "")
        end = "" if str(end).startswith("9999") else end
        pos = lang(it.get("job"))
        sect = lang(it.get("section"))
        affil = lang(it.get("affiliation"))
        work.append({
            "name": affil,
            "company": affil,  # cv-template.html reads work.company
            "position": (f"{pos}, {sect}" if sect else pos),
            "startDate": it.get("from_date", ""),
            "endDate": end,
            "summary": "",
            "highlights": [],
        })

    education = []
    for it in sorted(fetch("education"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        inst = lang(it.get("affiliation"))
        dept = lang(it.get("department"))
        education.append({
            "institution": (f"{inst}, {dept}" if dept else inst),
            "area": lang(it.get("course")),
            "studyType": "",
            "startDate": it.get("from_date", ""),
            "endDate": "" if str(it.get("to_date", "")).startswith("9999") else it.get("to_date", ""),
        })

    awards = []
    for it in sorted(fetch("awards"),
                     key=lambda x: x.get("award_date", ""), reverse=True):
        awards.append({
            "title": lang(it.get("award_name")),
            "date": it.get("award_date", ""),
            "awarder": lang(it.get("association")),
            "summary": lang(it.get("award_title")),
        })

    projects = []
    for it in sorted(fetch("research_projects"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        projects.append({
            "name": lang(it.get("research_project_title")),
            "startDate": it.get("from_date", ""),
            "endDate": "" if str(it.get("to_date", "")).startswith("9999") else it.get("to_date", ""),
            "description": lang(it.get("system_name")) or lang(it.get("category")),
            "entity": lang(it.get("offer_organization")),
        })

    volunteer = []
    for it in sorted(fetch("committee_memberships"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        volunteer.append({
            "organization": lang(it.get("association")),
            "position": lang(it.get("committee_name")),
            "startDate": it.get("from_date", ""),
            "endDate": "" if str(it.get("to_date", "")).startswith("9999") else it.get("to_date", ""),
        })

    current = work[0]["name"] if work else "The University of Tokyo"
    cv = {
        "basics": {
            "name": PROFILE["name"],
            "email": PROFILE["email"],
            "website": PROFILE["website"],
            "summary": f"Associate Professor at {current}.",
            "location": {"city": "Tokyo", "countryCode": "JP", "region": ""},
            "profiles": [
                {"network": "ORCID", "username": "", "url": PROFILE["orcid"]},
                {"network": "Google Scholar", "username": "",
                 "url": PROFILE["googlescholar"]},
                {"network": "GitHub", "username": PROFILE["github"],
                 "url": f"https://github.com/{PROFILE['github']}"},
                {"network": "researchmap", "username": PERMALINK,
                 "url": f"https://researchmap.jp/{PERMALINK}"},
            ] if PROFILE["googlescholar"] else [
                {"network": "ORCID", "username": "", "url": PROFILE["orcid"]},
                {"network": "GitHub", "username": PROFILE["github"],
                 "url": f"https://github.com/{PROFILE['github']}"},
                {"network": "researchmap", "username": PERMALINK,
                 "url": f"https://researchmap.jp/{PERMALINK}"},
            ],
        },
        "work": work,
        "education": education,
        "awards": awards,
        "projects": projects,
        "volunteer": volunteer,
        "publications": [],
        "skills": [],
    }
    (ROOT / "_data").mkdir(exist_ok=True)
    (ROOT / "_data" / "cv.json").write_text(
        json.dumps(cv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  _data/cv.json: {len(work)} positions, {len(education)} edu, "
          f"{len(awards)} awards, {len(projects)} grants, {len(volunteer)} committees")


def main():
    print(f"Building from researchmap: {PERMALINK}")
    gen_publications()
    gen_talks()
    gen_cv()
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
