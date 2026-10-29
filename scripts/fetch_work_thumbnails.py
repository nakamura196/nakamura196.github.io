#!/usr/bin/env python3
"""Fill in missing thumbnails for master/works.json (macOS: needs `sips`).

For each work without an image at images/works/<rm:id or x-local-id>.jpg:
  0. if ~/git/zenn (ldas.jp site, origin/main) lists the same site in
     web/src/lib/works.ts or web/public/data/projects.json (tools)
     (matched by normalized URL, else exact ja title),
     use that entry's image (source "ldas.jp works.ts");
  1. take the og:image / twitter:image of the work's URL;
  2. if that is missing, SVG, points to localhost, or fails to download,
     take a headless-Chrome screenshot of the page;
and resize to 640px wide JPEG (quality 80). Sets "x-thumbnail" and
"x-thumbnail-source" ("og:image" or "screenshot") on the item in master.
Never overwrites an existing image. Delete the file to refetch.

    python3 scripts/fetch_work_thumbnails.py [rm:id|x-local-id ...]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "master" / "works.json"
OUT = ROOT / "images" / "works"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def work_url(it: dict) -> str:
    for s in it.get("see_also") or []:
        if s.get("label") in ("url", "url_en") and s.get("@id"):
            return s["@id"]
    return ""


def http(url: str, limit=15_000_000) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(limit), r.headers.get("Content-Type", "")


def og_image(page_url: str) -> str:
    html = http(page_url)[0].decode("utf-8", "replace")
    for prop in ("og:image", "twitter:image"):
        for m in re.finditer(r"<meta\b[^>]*>", html, re.I):
            tag = m.group(0)
            if re.search(r'(?:property|name)\s*=\s*["\']%s["\']' % re.escape(prop), tag, re.I):
                c = re.search(r'content\s*=\s*["\']([^"\']+)', tag, re.I)
                if c:
                    return urllib.parse.urljoin(page_url, c.group(1).replace("&amp;", "&"))
    return ""


ZENN = Path.home() / "git" / "zenn"


def _norm(u: str) -> str:
    u = re.sub(r"^https?://", "", u.split("?")[0].split("#")[0])
    return re.sub(r"^www\.", "", u).rstrip("/")


def ldas_entries() -> list[dict]:
    """Parse WORKS in ldas.jp's works.ts (read via git; repo is not touched)."""
    r = subprocess.run(["git", "-C", str(ZENN), "show", "origin/main:web/src/lib/works.ts"],
                       capture_output=True, text=True)
    if r.returncode:
        return []
    t = r.stdout
    t = t[t.index("export const WORKS"):]
    out = []
    for b in re.split(r"\n  \{\n    id: ", t)[1:]:
        tj = re.search(r'title: \{\s*ja: "([^"]*)"', b)
        m = re.search(r'\n    url: \{\s*ja: "([^"]+)",\s*en: "([^"]+)"', b)
        urls = [m.group(1), m.group(2)] if m else re.findall(r'\n    url: same\("([^"]+)"\)', b)
        im = re.search(r'\n    image:\s*"([^"]+)"', b)
        if urls and im:
            out.append({"title": tj.group(1) if tj else "", "urls": urls, "image": im.group(1)})
    r = subprocess.run(["git", "-C", str(ZENN), "show", "origin/main:web/public/data/projects.json"],
                       capture_output=True, text=True)
    if not r.returncode:
        out += [{"title": t["title"], "urls": [t["url"]], "image": t["img"]}
                for t in json.loads(r.stdout) if t.get("url") and t.get("img")]
    return out


def from_ldas(entries: list[dict], it: dict, dst: Path, tmp: Path) -> bool:
    u = work_url(it)
    tj = (it.get("work_title") or {}).get("ja", "")
    hit = [e for e in entries if _norm(u) in [_norm(x) for x in e["urls"]]] or \
          [e for e in entries if e["title"] == tj]
    if not hit:
        return False
    img = hit[0]["image"]
    raw = tmp / "ldas.bin"
    if img.startswith("/"):
        r = subprocess.run(["git", "-C", str(ZENN), "show",
                            f"origin/main:web/public{img}"], capture_output=True)
        if r.returncode:
            return False
        raw = tmp / ("ldas" + Path(img).suffix)
        raw.write_bytes(r.stdout)
    else:
        raw.write_bytes(http(img)[0])
    return resize(raw, dst)


def resize(src: Path, dst: Path) -> bool:
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        "--resampleWidth", "640", str(src), "--out", str(dst)],
                       capture_output=True)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 0


def from_og(page_url: str, dst: Path, tmp: Path) -> bool:
    img = og_image(page_url)
    if not img or img.lower().split("?")[0].endswith(".svg") or re.match(
            r"https?://(localhost|127\.)", img):
        return False
    data, ctype = http(img)
    if "svg" in ctype or "image" not in ctype and not data[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1"):
        return False
    raw = tmp / "og.bin"
    raw.write_bytes(data)
    return resize(raw, dst)


def from_screenshot(page_url: str, dst: Path, tmp: Path) -> bool:
    raw = tmp / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
                    "--window-size=1280,720", "--virtual-time-budget=8000",
                    f"--screenshot={raw}", page_url], capture_output=True, timeout=120)
    return raw.exists() and raw.stat().st_size > 0 and resize(raw, dst)


def main() -> int:
    only = set(sys.argv[1:])
    works = json.loads(MASTER.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    changed = False
    entries = ldas_entries()
    for it in works:
        rid = it.get("rm:id") or it["x-local-id"]
        if only and rid not in only:
            continue
        dst = OUT / f"{rid}.jpg"
        title = (it.get("work_title") or {}).get("ja", rid)
        if dst.exists():
            if not it.get("x-thumbnail"):
                it["x-thumbnail"] = f"/images/works/{rid}.jpg"
                changed = True
            continue
        url = work_url(it)
        if not url:
            print(f"- {title}: no URL")
            continue
        src = None
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            try:
                if from_ldas(entries, it, dst, tmp):
                    src = "ldas.jp works.ts"
            except Exception as e:
                print(f"  ldas failed {title}: {e}")
            try:
                if not src and from_og(url, dst, tmp):
                    src = "og:image"
            except Exception as e:
                print(f"  og failed {title}: {e}")
            if not src:
                try:
                    if from_screenshot(url, dst, tmp):
                        src = "screenshot"
                except Exception as e:
                    print(f"  screenshot failed {title}: {e}")
        if src:
            it["x-thumbnail"] = f"/images/works/{rid}.jpg"
            it["x-thumbnail-source"] = src
            changed = True
            print(f"+ {title}: {src} ({dst.stat().st_size // 1024} KB)")
        else:
            dst.unlink(missing_ok=True)
            print(f"- {title}: NONE ({url})")
    if changed:
        MASTER.write_text(json.dumps(works, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
