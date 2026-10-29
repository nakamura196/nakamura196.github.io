#!/usr/bin/env python3
"""One-time (re-)seeding of master/ from the researchmap public API.

Writes master/<kind>.json (the API's `items` array, untouched) and
master/profile.json (the root object). Existing master files are NOT
overwritten unless --force is given, because master/ is the source of truth
and may hold local edits and `x-` fields.

    python3 scripts/rm_export_to_master.py [--force]
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


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if not isinstance(data, dict):
        raise ValueError("unexpected response")
    return data


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def main() -> int:
    force = "--force" in sys.argv
    MASTER.mkdir(exist_ok=True)
    try:
        profile = get(f"{API}/{PERMALINK}")
        data = {k: get(f"{API}/{PERMALINK}/{k}?limit=2000").get("items") or []
                for k in KINDS}
    except Exception as e:
        print(f"network failure: {e}", file=sys.stderr)
        return 2
    targets = [(MASTER / "profile.json", profile)] + \
              [(MASTER / f"{k}.json", v) for k, v in data.items()]
    for path, obj in targets:
        if path.exists() and not force:
            print(f"  skip (exists): {path.name}")
            continue
        dump(path, obj)
        print(f"  wrote {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
