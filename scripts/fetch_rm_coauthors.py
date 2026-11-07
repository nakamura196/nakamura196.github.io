#!/usr/bin/env python3
"""Fetch the owner's co-authors from researchmap (permalink + name only).

researchmap's co-author list is only reachable from Japan (VPN needed from
abroad), so this is NOT part of the daily GitHub Actions sync. Run it by hand
now and then; new co-authors simply have no researchmap link until then.

    python3 scripts/fetch_rm_coauthors.py          # writes scripts/coauthor_researchmap.json

The endpoint also returns small profile photos (base64); they are dropped.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

OWNER = "nakamura.satoru"
URL = f"https://researchmap.jp/{OWNER}/coauthors/coauthors/index"
OUT = Path(__file__).with_name("coauthor_researchmap.json")
HEAD = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}


def page(search_after):
    q = ""
    if search_after:
        q = "?" + "&".join("search_after[]=" + urllib.parse.quote(json.dumps(v) if isinstance(v, bool) else str(v)) for v in search_after)
    with urllib.request.urlopen(urllib.request.Request(URL + q, headers=HEAD), timeout=30) as r:
        body = r.read().decode("utf-8").strip()
    return json.loads(body) if body else {}


def main():
    people, seen, sa = [], set(), None
    for _ in range(500):
        x = page(sa)
        new = 0
        for c in x.get("coauthors") or []:
            rel = c.get("Related") or {}
            p = rel.get("permalink")
            if p and p not in seen:
                seen.add(p); new += 1
                people.append({"name": rel.get("name_str", ""), "permalink": p})
        if not new or not x.get("search_after"):
            break
        sa = x["search_after"]
        time.sleep(0.3)
    if not people:
        raise SystemExit("取得できませんでした（国外からは VPN が要ります）")
    OUT.write_text(json.dumps({
        "_note": "researchmap の共著者（名前と個人ページの ID のみ。写真は保存しない）。"
                 "scripts/fetch_rm_coauthors.py で取り直す。VPN が要る。",
        "fetched": date.today().isoformat(),
        "people": people,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(people)} people -> {OUT.name}")


if __name__ == "__main__":
    main()
