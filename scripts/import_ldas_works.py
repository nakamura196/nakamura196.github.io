#!/usr/bin/env python3
"""Add works and tools listed on ldas.jp but missing from master/works.json.

researchmap has no separate category for software, so tools (/tools, from
web/public/data/projects.json) go into works too. Hidden tools are skipped;
a tool whose public run has ended gets that month as `to_date`.

Reads WORKS from ~/git/zenn web/src/lib/works.ts at origin/main (via git and
Node's type stripping; the zenn checkout is not touched). A work counts as
already present when its normalized URL (ja or en) or its ja title matches an
item in master, or when its id is listed in SKIP. New items get no `rm:id`
(they are local additions; export_researchmap.py picks them up) and carry
`x-local-id: ldas-<id>` so thumbnails can be stored as images/works/ldas-<id>.jpg.
Titles and descriptions are copied as written on ldas.jp, in both languages.

    python3 scripts/import_ldas_works.py           # dry run
    python3 scripts/import_ldas_works.py --write
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_work_thumbnails import MASTER, ZENN, _norm  # noqa: E402

# Same work as an existing researchmap item, under a different URL.
SKIP = {
    "daizokyo",  # 酉蓮社 (ldas.jp points to u-renja.toyobunko-lab.jp)
}


def ldas_works() -> list[dict]:
    src = subprocess.run(["git", "-C", str(ZENN), "show", "origin/main:web/src/lib/works.ts"],
                         capture_output=True, text=True, check=True).stdout
    src = "\n".join(l for l in src.splitlines() if not l.startswith("import type "))
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "works.ts"
        f.write_text(src, encoding="utf-8")
        out = subprocess.run(
            ["node", "--experimental-strip-types", "--no-warnings", "-e",
             f'import({json.dumps(str(f))}).then(m => console.log(JSON.stringify(m.WORKS)))'],
            capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def ldas_tools() -> list[dict]:
    src = subprocess.run(["git", "-C", str(ZENN), "show", "origin/main:web/public/data/projects.json"],
                         capture_output=True, text=True, check=True).stdout
    out = []
    for t in json.loads(src):
        if t.get("hidden") or not t.get("url"):
            continue
        out.append({
            "id": t["id"],
            "title": {"ja": t["title"], "en": t["en"]},
            "description": {"ja": t["desc"], "en": t.get("enDesc") or ""},
            "url": {"ja": t["url"], "en": t["url"]},
            "since": t.get("date") or t.get("lastmod") or "",
            "ended": t.get("ended"),
            "source": t.get("source"),
            "image": t.get("img"),
            "kind": "tool",
        })
    return out


def to_item(w: dict) -> dict:
    see_also = [{"@id": w["url"]["ja"], "label": "url", "is_downloadable": False}]
    if _norm(w["url"]["en"]) != _norm(w["url"]["ja"]):
        see_also.append({"@id": w["url"]["en"], "label": "url_en", "is_downloadable": False})
    if w.get("source"):
        see_also.append({"@id": w["source"], "label": "url", "is_downloadable": False})
    page = "tools" if w.get("kind") == "tool" else "projects"
    desc = {k: v for k, v in w["description"].items() if v}
    return {
        "@type": "works",
        "display": "disclosed",
        "work_title": {"ja": w["title"]["ja"], "en": w["title"]["en"]},
        "creators": {"ja": [{"name": "中村覚"}], "en": [{"name": "Satoru Nakamura"}]},
        "from_date": w["since"][:7],
        "to_date": w["ended"][:7] if w.get("ended") else "9999",
        "description": desc,
        "see_also": see_also,
        "x-local-id": f"ldas-{w['id']}",
        "x-source": f"https://ldas.jp/ja/{page}/ (id: {w['id']})",
    }


def main() -> int:
    works = json.loads(MASTER.read_text(encoding="utf-8"))
    urls = {_norm(u) for it in works for u in
            [s.get("@id", "") for s in it.get("see_also") or []] if u}
    titles = {(it.get("work_title") or {}).get("ja") for it in works}
    local = {it.get("x-local-id") for it in works}
    added = []
    for w in ldas_works() + ldas_tools():
        if w["id"] in SKIP or f"ldas-{w['id']}" in local:
            continue
        if {_norm(w["url"]["ja"]), _norm(w["url"]["en"])} & urls or w["title"]["ja"] in titles:
            continue
        added.append(to_item(w))
        print(f"+ {w['since'][:7]} {w['title']['ja']}")
    print(f"{len(added)} to add")
    if "--write" in sys.argv and added:
        works += added
        MASTER.write_text(json.dumps(works, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
