#!/usr/bin/env python3
"""Build the /projects/ pages and the JSON Resume download from projects/*.md.

Source (edit these): projects/<id>.md (English) and projects/<id>.ja.md (Japanese).
Each file has YAML front matter (name, organization, position, start, end, url,
status, notes) and these sections, each a paragraph or a bullet list:

  ## Role / 役割              paragraph
  ## Outputs / 作品           - [Name](url) YYYY-MM
  ## Related grants / 関連する研究費   - Title | period | number | position
  ## Evidence / 根拠           - free text

Writes:
  - files/export/projects.json, files/export/projects.ja.json  (JSON Resume, "projects" section)
  - _includes/gen/list-projects-{en,ja}.html                   (static HTML, no JavaScript)

Usage: python3 scripts/build_projects.py
"""
import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "projects"
ORDER = ["utokyo-digital-archives", "toyo-bunko", "rekihaku", "ndl", "cultural-japan", "digital-genji"]

SECTIONS = {
    "Role": "role", "役割": "role",
    "Outputs": "outputs", "作品": "outputs",
    "Related grants": "grants", "関連する研究費": "grants",
    "Evidence": "evidence", "根拠": "evidence",
}
T = {
    "en": {"present": "present", "outputs": "Outputs", "grants": "Related grants", "evidence": "Evidence",
           "draft": "Draft — to be confirmed", "org": "Organization", "position": "Position",
           "period": "Period", "role": "Role", "works": "/works/"},
    "ja": {"present": "現在", "outputs": "作品", "grants": "関連する研究費", "evidence": "根拠",
           "draft": "下書き（要確認）", "org": "機関", "position": "職名",
           "period": "期間", "role": "役割", "works": "/ja/works/"},
}
OUTPUT_RE = re.compile(r"^\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?P<date>\d{4}-\d{2})?\s*$")


def work_ids():
    """Map a work's URL to its x-local-id in master/works.json, to link to /works/<id>."""
    ids = {}
    for w in json.loads((ROOT / "master" / "works.json").read_text()):
        if w.get("x-local-id"):
            for s in w.get("see_also", []):
                ids[s["@id"].rstrip("/")] = w["x-local-id"]
    return ids


def parse(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: missing front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    body = {"role": [], "outputs": [], "grants": [], "evidence": []}
    sec = None
    for line in m.group(2).splitlines():
        if line.startswith("## "):
            sec = SECTIONS.get(line[3:].strip())
            if sec is None:
                raise SystemExit(f"{path}: unknown section {line!r}")
        elif sec and line.strip():
            body[sec].append(line.strip())
    return meta, body


def to_project(pid, meta, body, ids):
    p = {"name": meta["name"], "entity": meta.get("organization") or "",
         "roles": [meta["position"]] if meta.get("position") else [],
         "startDate": str(meta.get("start") or ""), "url": meta.get("url") or "",
         "description": " ".join(body["role"]), "type": "project"}
    if meta.get("end"):
        p["endDate"] = str(meta["end"])
    outputs = []
    for line in body["outputs"]:
        mo = OUTPUT_RE.match(line.removeprefix("- "))
        if not mo:
            raise SystemExit(f"{pid}: cannot read output line {line!r}")
        o = {"name": mo["name"], "url": mo["url"], "startDate": mo["date"] or ""}
        if mo["url"].rstrip("/") in ids:
            o["x-local-id"] = ids[mo["url"].rstrip("/")]
        outputs.append(o)
    p["highlights"] = [o["name"] for o in outputs]
    p["x-id"] = pid
    p["x-outputs"] = outputs
    grants = []
    for line in body["grants"]:
        cells = [c.strip() for c in line.removeprefix("- ").split("|")]
        if len(cells) != 4:
            raise SystemExit(f"{pid}: grant line needs 4 fields separated by |: {line!r}")
        grants.append(dict(zip(["name", "period", "grantNumber", "role"], cells)))
    if grants:
        p["x-grants"] = grants
    p["x-evidence"] = [x.removeprefix("- ") for x in body["evidence"]]
    if meta.get("notes"):
        p["x-notes"] = meta["notes"]
    if meta.get("status"):
        p["x-status"] = meta["status"]
    return p


def e(s):
    return html.escape(str(s or ""))


def build_html(projects, lang):
    t = T[lang]
    out = ['<div class="rm-projects">']
    for p in projects:
        out.append(f'<section class="rm-sec rm-project" id="{e(p["x-id"])}">')
        out.append(f'<h2>{e(p["name"])}</h2>')
        if p.get("x-status") == "draft":
            out.append(f'<p class="rm-meta"><strong>{e(t["draft"])}</strong></p>')
        end = p.get("endDate") or t["present"]
        out.append("<dl>")
        out.append(f'<dt>{t["org"]}</dt><dd>{e(p["entity"])}</dd>')
        if p["roles"]:
            out.append(f'<dt>{t["position"]}</dt><dd>{e("; ".join(p["roles"]))}</dd>')
        out.append(f'<dt>{t["period"]}</dt><dd>{e(p["startDate"])} – {e(end)}</dd>')
        for k, v in (p.get("x-notes") or {}).items():
            out.append(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
        out.append(f'<dt>{t["role"]}</dt><dd>{e(p["description"])}</dd>')
        out.append("</dl>")
        out.append(f'<h3>{t["outputs"]}</h3><ul>')
        for o in p["x-outputs"]:
            name = e(o["name"])
            if o.get("x-local-id"):
                name = f'<a href="{t["works"]}{e(o["x-local-id"])}">{name}</a>'
            out.append(f'<li>{name} ({e(o["startDate"])}) <a class="rm-link" href="{e(o["url"])}">↗</a></li>')
        out.append("</ul>")
        if p.get("x-grants"):
            out.append(f'<h3>{t["grants"]}</h3><ul>')
            for g in p["x-grants"]:
                out.append(f'<li>{e(g["name"])} — {e(g["period"])}, {e(g["grantNumber"])}, {e(g["role"])}</li>')
            out.append("</ul>")
        if p["x-evidence"]:
            out.append(f'<h3>{t["evidence"]}</h3><ul>')
            out += [f"<li>{e(x)}</li>" for x in p["x-evidence"]]
            out.append("</ul>")
        out.append("</section>")
    out.append("</div>")
    return "\n".join(out) + "\n"


def main():
    ids = work_ids()
    for lang, suffix, export in [("en", ".md", "projects.json"), ("ja", ".ja.md", "projects.ja.json")]:
        projects = [to_project(pid, *parse(SRC / f"{pid}{suffix}"), ids) for pid in ORDER]
        doc = {
            "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
            "meta": {"lang": lang, "note": "Generated from projects/*.md by scripts/build_projects.py. "
                     "Fields starting with x- are local extensions to JSON Resume."},
            "projects": projects,
        }
        (ROOT / "files" / "export" / export).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        (ROOT / "_includes" / "gen" / f"list-projects-{lang}.html").write_text(build_html(projects, lang))
        print(f"{lang}: {len(projects)} projects -> files/export/{export}")


if __name__ == "__main__":
    main()
