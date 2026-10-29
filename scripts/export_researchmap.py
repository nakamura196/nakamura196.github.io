#!/usr/bin/env python3
"""Write the items to submit to researchmap: build/researchmap-import.jsonl

Included:
  - items in master/ without `rm:id` (local-only additions)
  - items whose content differs from the researchmap API (see rm_diff.py)
All `x-*` fields are removed.

NOTE (unverified format): researchmap's official import (JSON Lines) wrapper
format could not be verified (spec page unreachable when this was written).
Each line is therefore the plain item JSON plus a `"type": "<kind>"` key.
Check against researchmap's import specification before uploading, and adapt
`wrap()` below if the format differs.

Read-only toward master/ and the site. Exit 2 on network failure.

    python3 scripts/export_researchmap.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rm_diff  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "build" / "researchmap-import.jsonl"


def clean(item: dict) -> dict:
    return {k: v for k, v in item.items() if not k.startswith("x-")}


def wrap(kind: str, item: dict) -> dict:
    # UNVERIFIED wrapper: see module docstring.
    return {"type": kind, **clean(item)}


def main() -> int:
    rows = []
    try:
        for kind in rm_diff.KINDS:
            _, only_master, changed = rm_diff.compare(kind)
            rows += [wrap(kind, i) for i in only_master if "rm:id" not in i]
            rows += [wrap(kind, m) for m, _, _ in changed]
    except Exception as e:
        print(f"network failure: {e}", file=sys.stderr)
        return 2
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                   encoding="utf-8")
    print(f"{len(rows)} items -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
