#!/usr/bin/env python3
"""Generate the site content from the local master (master/*.json).

master/ holds the achievement data in researchmap API format and is the
source of truth (see README "master"). Writes:
  - _publications/*.md   (books, journal/proceedings papers, misc articles)
  - _talks/*.md          (presentations)
  - _data/cv.json        (jsonresume: basics, work, education, awards,
                          research grants, committee memberships)

Re-runnable: regenerates the above from scratch on every run. Hand edits
to generated files are intentionally overwritten — edit master/ instead.
Fields prefixed `x-` in master are local-only (e.g. x-thumbnail).

Usage:
    python3 scripts/build_site.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PERMALINK = os.environ.get("PERMALINK", "nakamura.satoru")
API = "https://api.researchmap.jp"
ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "master"
_JA = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")

# --- static profile bits not in researchmap (edit here) ---
PROFILE = {
    "name": "Satoru Nakamura",
    "name_ja": "中村 覚",
    "email": "",
    "website": "https://nakamura196.github.io",
    "orcid": "https://orcid.org/0000-0001-8245-7925",
    "github": "nakamura196",
    "googlescholar": "https://scholar.google.com/citations?user=gbuswBEAAAAJ",
    "semanticscholar": "https://www.semanticscholar.org/author/2111225943",
    "dblp": "https://dblp.org/pid/51/6055.html",
}


class FetchError(RuntimeError):
    pass


_fetched: dict[str, list[dict]] = {}


def fetch(kind: str) -> list[dict]:
    """Read all items of one achievement type from master/<kind>.json."""
    if kind in _fetched:
        return _fetched[kind]
    f = MASTER / f"{kind}.json"
    try:
        items = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        raise FetchError(f"{kind}: unreadable ({e})") from e
    if not isinstance(items, list):
        raise FetchError(f"{kind}: expected a list")
    _fetched[kind] = items
    return items


_root: dict = {}


def fetch_root() -> dict:
    """Read the researcher's basic profile (affiliation, degrees, bio)."""
    if _root:
        return _root
    try:
        data = json.loads((MASTER / "profile.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "family_name" not in data:
            raise ValueError("unexpected content")
    except Exception as e:
        raise FetchError(f"profile: unreadable ({e})") from e
    _root.update(data)
    return _root


def end_date(d) -> str:
    """researchmap uses 9999 for 'present'."""
    return "" if str(d or "").startswith("9999") else (d or "")


def link(it: dict) -> str:
    """First plain URL in an item's see_also, if any."""
    for s in it.get("see_also") or []:
        if s.get("label") in ("url", "url_en") and s.get("@id"):
            return s["@id"]
    return ""


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


def names(field, prefer="en"):
    """Join an author/presenter list (prefer en list) into 'A, B, C'."""
    if not isinstance(field, dict):
        return ""
    other = "ja" if prefer == "en" else "en"
    lst = field.get(prefer) or field.get(other) or []
    out = []
    for n in lst:
        name = n.get("name", "")
        if _JA.search(name):  # "中村, 覚" → "中村 覚"
            name = name.replace(", ", " ").replace(",", " ")
        if name:
            out.append(name)
    return ", ".join(out)


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


def kaken_url(it: dict) -> str:
    grant = (it.get("identifiers") or {}).get("grant_number")
    if isinstance(grant, list) and grant:
        return f"https://kaken.nii.ac.jp/grant/KAKENHI-PROJECT-{grant[0]}/"
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
        title_ja = lang(it.get("book_title"), "ja") or title
        venue_ja = lang(it.get("publisher"), "ja")
        cite_ja = f'{names(it.get("authors"), "ja")}『{title_ja}』{venue_ja}, {y(date)}.'
        write_md(out / f"{date}-book-{rid}.md", {
            "title": title,
            "title_ja": title_ja,
            "venue_ja": venue_ja,
            "citation_ja": cite_ja,
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
        title_ja = lang(it.get("paper_title"), "ja") or title
        venue_ja = lang(it.get("publication_name"), "ja")
        cite_ja = f'{names(it.get("authors"), "ja")}「{title_ja}」『{venue_ja}』'
        if vol:
            cite_ja += f", {vol}"
        if pages:
            cite_ja += f", pp.{pages}"
        cite_ja += f", {y(date)}."
        if it.get("referee"):
            bits += " [refereed]"
            cite_ja += "［査読有り］"
        write_md(out / f"{date}-paper-{rid}.md", {
            "title": title,
            "title_ja": title_ja,
            "venue_ja": venue_ja,
            "citation_ja": cite_ja,
            "refereed": "true" if it.get("referee") else "",
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
        title_ja = lang(it.get("paper_title"), "ja") or title
        venue_ja = lang(it.get("publication_name"), "ja")
        cite_ja = f'{names(it.get("authors"), "ja")}「{title_ja}」『{venue_ja}』, {y(date)}.'
        write_md(out / f"{date}-misc-{rid}.md", {
            "title": title,
            "title_ja": title_ja,
            "venue_ja": venue_ja,
            "citation_ja": cite_ja,
            "paperurl": doi_url(it.get("identifiers", {})),
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
        ptype_ja = {
            "Oral presentation": "口頭発表",
            "Poster": "ポスター発表",
            "Symposium": "シンポジウム",
            "Keynote": "基調講演",
            "Invited talk": "招待講演",
        }.get(ptype, "招待講演" if ptype.startswith("Invited") else ptype)
        write_md(out / f"{date}-talk-{rid}.md", {
            "title": title,
            "title_ja": lang(it.get("presentation_title"), "ja") or title,
            "venue_ja": lang(it.get("event"), "ja"),
            "authors": names(it.get("presenters")),
            "authors_ja": names(it.get("presenters"), "ja"),
            "type_ja": ptype_ja,
            "invited": "true" if it.get("invited") else "",
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
def gen_cv(prefer: str = "en", filename: str = "cv.json"):
    work = []
    for it in sorted(fetch("research_experience"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        end = end_date(it.get("to_date"))
        pos = lang(it.get("job"), prefer)
        sect = lang(it.get("section"), prefer)
        affil = lang(it.get("affiliation"), prefer)
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
                     key=lambda x: x.get("to_date") or x.get("from_date", ""),
                     reverse=True):
        inst = lang(it.get("affiliation"), prefer)
        dept = lang(it.get("department"), prefer)
        education.append({
            "institution": (f"{inst}, {dept}" if dept else inst),
            "area": lang(it.get("course"), prefer),
            "studyType": "",
            "startDate": it.get("from_date", ""),
            "endDate": end_date(it.get("to_date")),
        })

    awards = []
    for it in sorted(fetch("awards"),
                     key=lambda x: x.get("award_date", ""), reverse=True):
        awards.append({
            "title": lang(it.get("award_name"), prefer),
            "date": it.get("award_date", ""),
            "awarder": lang(it.get("association"), prefer),
            "summary": lang(it.get("award_title"), prefer),
        })

    projects = []
    for it in sorted(fetch("research_projects"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        projects.append({
            "name": lang(it.get("research_project_title"), prefer),
            "startDate": it.get("from_date", ""),
            "endDate": end_date(it.get("to_date")),
            "description": lang(it.get("system_name"), prefer) or lang(it.get("category"), prefer),
            "entity": lang(it.get("offer_organization"), prefer),
            "nameJa": lang(it.get("research_project_title"), "ja"),
            "investigators": names(it.get("investigators"), prefer),
            "url": link(it) or kaken_url(it),
        })

    volunteer = []
    for it in sorted(fetch("committee_memberships"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        volunteer.append({
            "organization": lang(it.get("association"), prefer),
            "position": lang(it.get("committee_name"), prefer),
            "startDate": it.get("from_date", ""),
            "endDate": end_date(it.get("to_date")),
        })

    # Current post from the profile's affiliation (not the newest work entry,
    # which may be a visiting position). Institution only, no department.
    aff = (fetch_root().get("affiliations") or [{}])[0]
    if prefer == "ja":
        summary = f'{lang(aff.get("affiliation"), "ja")} {lang(aff.get("job"), "ja")}'
    else:
        summary = f'{lang(aff.get("job"))}, {lang(aff.get("affiliation"))}'
    interests = [{"name": lang(it.get("research_field"), prefer), "keywords": []}
                 for it in fetch("research_areas")]
    kw = [lang(it.get("keyword"), prefer) for it in fetch("research_interests")]
    if kw:
        interests.append({"name": "キーワード" if prefer == "ja" else "Keywords",
                          "keywords": kw})
    cv = {
        "basics": {
            "name": PROFILE["name_ja"] if prefer == "ja" else PROFILE["name"],
            "website": PROFILE["website"],
            "summary": summary,
            "location": {"city": "Tokyo", "countryCode": "JP"},
            "profiles": [
                p for p in [
                    {"network": "ORCID", "username": "", "url": PROFILE["orcid"]},
                    {"network": "Google Scholar", "username": "",
                     "url": PROFILE["googlescholar"]},
                    {"network": "Semantic Scholar", "username": "",
                     "url": PROFILE["semanticscholar"]},
                    {"network": "DBLP", "username": "", "url": PROFILE["dblp"]},
                    {"network": "GitHub", "username": PROFILE["github"],
                     "url": f"https://github.com/{PROFILE['github']}"},
                    {"network": "researchmap", "username": PERMALINK,
                     "url": f"https://researchmap.jp/{PERMALINK}"},
                ] if p["url"]
            ],
        },
        "work": work,
        "education": education,
        "awards": awards,
        "projects": projects,
        "volunteer": volunteer,
        "interests": interests,
        "publications": [],
        "skills": [],
    }
    (ROOT / "_data").mkdir(exist_ok=True)
    (ROOT / "_data" / filename).write_text(
        json.dumps(cv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  _data/{filename}: {len(work)} positions, {len(education)} edu, "
          f"{len(awards)} awards, {len(projects)} grants, {len(volunteer)} committees")


# --------------------------------------------------------------------------
# Everything else on researchmap: profile, works, memberships, outreach,
# research areas/keywords, counts → _data/researchmap.json
# --------------------------------------------------------------------------
def gen_profile_data():
    root = fetch_root()

    affiliations = [{
        "institution": lang(a.get("affiliation")),
        "institutionJa": lang(a.get("affiliation"), "ja"),
        "section": lang(a.get("section")),
        "sectionJa": lang(a.get("section"), "ja"),
        "job": lang(a.get("job")),
        "jobJa": lang(a.get("job"), "ja"),
    } for a in root.get("affiliations") or []]

    degrees = [{
        "degree": lang(d.get("degree")),
        "institution": lang(d.get("degree_institution")),
        "date": d.get("degree_date", ""),
    } for d in root.get("degrees") or []]

    works = []
    for it in sorted(fetch("works"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        works.append({
            "title": lang(it.get("work_title")),
            "titleJa": lang(it.get("work_title"), "ja"),
            "creators": names(it.get("creators")),
            "creatorsJa": names(it.get("creators"), "ja"),
            "startDate": it.get("from_date", ""),
            "endDate": end_date(it.get("to_date")),
            "url": link(it),
            "description": lang(it.get("description")),
            "descriptionJa": lang(it.get("description"), "ja"),
            **({"thumbnail": it["x-thumbnail"]} if it.get("x-thumbnail") else {}),
        })

    memberships = []
    for it in sorted(fetch("association_memberships"),
                     key=lambda x: x.get("from_date", ""), reverse=True):
        memberships.append({
            "name": lang(it.get("academic_society_name")),
            "nameJa": lang(it.get("academic_society_name"), "ja"),
            "startDate": it.get("from_date", ""),
            "endDate": end_date(it.get("to_date")),
        })

    outreach = []
    for it in sorted(fetch("social_contribution"),
                     key=lambda x: x.get("from_event_date", ""), reverse=True):
        outreach.append({
            "title": lang(it.get("social_contribution_title")),
            "titleJa": lang(it.get("social_contribution_title"), "ja"),
            "promoterJa": lang(it.get("promoter"), "ja"),
            "promoter": lang(it.get("promoter")),
            "event": lang(it.get("event")),
            "date": it.get("from_event_date", ""),
            "endDate": end_date(it.get("to_event_date")),
            "type": (it.get("social_contribution_type") or "").replace("_", " "),
            "url": link(it),
        })

    areas = [{
        "discipline": lang(it.get("discipline")),
        "field": lang(it.get("research_field")),
        "fieldJa": lang(it.get("research_field"), "ja"),
    } for it in fetch("research_areas")]
    keywords = [lang(it.get("keyword")) for it in fetch("research_interests")]
    keywords_ja = [lang(it.get("keyword"), "ja") for it in fetch("research_interests")]

    papers = fetch("published_papers")
    talks = fetch("presentations")
    counts = {
        "papers": len(papers),
        "refereed": sum(1 for it in papers if it.get("referee")),
        "books": len(fetch("books_etc")),
        "misc": len(fetch("misc")),
        "talks": len(talks),
        "invited": sum(1 for it in talks if it.get("invited")),
        "works": len(works),
        "awards": len(fetch("awards")),
        "grants": len(fetch("research_projects")),
        "committees": len(fetch("committee_memberships")),
    }

    data = {
        "permalink": PERMALINK,
        "url": f"https://researchmap.jp/{PERMALINK}",
        "name": " ".join(filter(None, [lang(root.get("given_name")),
                                        lang(root.get("family_name"))])),
        "nameJa": " ".join(filter(None, [lang(root.get("family_name"), "ja"),
                                          lang(root.get("given_name"), "ja")])),
        "profileJa": lang(root.get("profile"), "ja"),
        "profileEn": (root.get("profile") or {}).get("en", ""),
        "affiliations": affiliations,
        "degrees": degrees,
        "degreesJa": [{
            "degree": lang(d.get("degree"), "ja"),
            "institution": lang(d.get("degree_institution"), "ja"),
            "date": d.get("degree_date", ""),
        } for d in root.get("degrees") or []],
        "researchAreas": areas,
        "keywords": keywords,
        "keywordsJa": keywords_ja,
        "works": works,
        "memberships": memberships,
        "outreach": outreach,
        "counts": counts,
    }
    (ROOT / "_data" / "researchmap.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  _data/researchmap.json: {len(works)} works, "
          f"{len(memberships)} memberships, {len(outreach)} outreach, "
          f"{len(keywords)} keywords")


def main():
    print("Building from master/")
    # Read everything first: if master is broken, stop before touching
    # any generated file.
    try:
        for kind in ("books_etc", "published_papers", "misc", "presentations",
                     "research_experience", "education", "awards",
                     "research_projects", "committee_memberships", "works",
                     "association_memberships", "social_contribution",
                     "research_areas", "research_interests"):
            fetch(kind)
        fetch_root()
    except FetchError as e:
        print(f"Aborted, nothing changed: {e}", file=sys.stderr)
        return 1
    if not _fetched["published_papers"] or not _fetched["presentations"]:
        print("Aborted, nothing changed: master has no papers/talks",
              file=sys.stderr)
        return 1
    gen_publications()
    gen_talks()
    gen_cv()
    gen_cv("ja", "cv_ja.json")
    gen_profile_data()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
