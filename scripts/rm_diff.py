#!/usr/bin/env python3
"""Compare master/ with the live researchmap API and print a Markdown report.

Per kind, matched by `rm:id`:
  - only on researchmap (e.g. auto-added from KAKEN / CiNii)
  - only in master (local additions without rm:id, or removed on researchmap)
  - content differs (field names listed)
Fields starting with `x-` and volatile metadata (modification timestamps,
modifier ids, API self-links) are ignored.

Read-only: never writes master or site files. Exit 0 even when differences
exist; exit 2 if the network fails.

    python3 scripts/rm_diff.py > diff.md
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

PERMALINK = os.environ.get("PERMALINK", "nakamura.satoru")
API = "https://api.researchmap.jp"
MASTER = Path(__file__).resolve().parent.parent / "master"
KINDS = ("books_etc", "published_papers", "misc", "presentations",
         "research_experience", "education", "awards", "research_projects",
         "committee_memberships", "works", "association_memberships",
         "social_contribution", "research_areas", "research_interests")
VOLATILE = {"rm:modified", "rm:modifier_id", "rm:modifier_type", "@id", "@reverse"}
# If a record was edited only on one side, `rm:created`-type fields still match.


def fetch_api(kind: str) -> list[dict]:
    url = f"{API}/{PERMALINK}/{kind}?limit=2000"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("items") or []


def strip(item: dict) -> dict:
    return {k: v for k, v in item.items()
            if not k.startswith("x-") and k not in VOLATILE}


def master_items(kind: str) -> list[dict]:
    return json.loads((MASTER / f"{kind}.json").read_text(encoding="utf-8"))


def label(item: dict) -> str:
    for k, v in item.items():
        if k.endswith("_title") or k in ("award_name", "academic_society_name",
                                         "committee_name", "keyword", "event",
                                         "research_field", "affiliation"):
            if isinstance(v, dict):
                return v.get("ja") or v.get("en") or ""
    return item.get("rm:id", "?")


def compare(kind: str, remote: list[dict] | None = None):
    """Return (only_remote, only_master, changed[(master_item, remote_item, fields)])."""
    remote = fetch_api(kind) if remote is None else remote
    local = master_items(kind)
    rmap = {i["rm:id"]: i for i in remote if "rm:id" in i}
    lmap = {i["rm:id"]: i for i in local if "rm:id" in i}
    only_remote = [rmap[k] for k in rmap if k not in lmap]
    only_master = [i for i in local if "rm:id" not in i] + \
                  [lmap[k] for k in lmap if k not in rmap]
    changed = []
    for k in lmap.keys() & rmap.keys():
        a, b = strip(lmap[k]), strip(rmap[k])
        fields = sorted(f for f in a.keys() | b.keys() if a.get(f) != b.get(f))
        if fields:
            changed.append((lmap[k], rmap[k], fields))
    return only_remote, only_master, changed


def main() -> int:
    lines = ["# researchmap と手元のマスタの差分", ""]
    total = 0
    sections = []
    try:
        for kind in KINDS:
            orem, omas, chg = compare(kind)
            n = len(orem) + len(omas) + len(chg)
            total += n
            if not n:
                continue
            sec = [f"## {kind}", ""]
            if orem:
                sec.append("researchmap にだけある（手元に無い）:")
                sec += [f"- {i['rm:id']} {label(i)}" for i in orem]
                sec.append("")
            if omas:
                sec.append("マスタにだけある:")
                sec += [f"- {i.get('rm:id') or '(rm:id なし)'} {label(i)}" for i in omas]
                sec.append("")
            if chg:
                sec.append("内容が違う:")
                sec += [f"- {m['rm:id']} {label(m)}: {', '.join(f)}" for m, _, f in chg]
                sec.append("")
            sections.append("\n".join(sec))
    except Exception as e:
        print(f"network failure: {e}", file=sys.stderr)
        return 2
    if not total:
        lines.append("差分はありません。")
    else:
        lines.append(f"差分 {total} 件。マスタ（master/）が正本です。"
                     "researchmap 側にだけある項目は、必要なら master/ に取り込んでください。")
        lines.append("")
        lines += sections
    print("\n".join(lines))
    print(f"total differences: {total}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
