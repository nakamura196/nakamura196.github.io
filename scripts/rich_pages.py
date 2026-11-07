"""Detail pages, filterable lists, exports and the co-researchers page.

Called from build_site.py (`init(B)` first, `finish()` last, B = build_site
module for its helpers). Everything here is derived from master/*.json;
generated files are overwritten on every run.

Writes:
  _pages/gen/{en,ja}/*.html   detail pages (en papers/talks are written by
                              build_site into _publications/_talks instead)
  _includes/gen/list-*.html   list bodies with filter data attributes
  _pages/coauthors.html, _pages/ja/coauthors.html
  files/export/               CSV per list, .bib per item, JSON per item
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

B = None            # build_site module
E = {}              # kind -> [entry]; entry = dict (see _entry)
BYID = {}           # rm:id / local id -> entry
SUP = {}            # superseded project id -> current project id
ENT = {}            # coauthor key -> entity
OWNER = {"中村覚", "satorunakamura", "nakamuranakamurasatoru", "nakamurasatoru"}

# kind -> (master file, rm path, people field, url prefix, list key)
KINDS = {
    "paper": ("published_papers", "published_papers", "authors"),
    "misc": ("misc", "misc", "authors"),
    "book": ("books_etc", "books_etc", "authors"),
    "talk": ("presentations", "presentations", "presenters"),
    "work": ("works", "works", "creators"),
    "project": ("research_projects", "research_projects", "investigators"),
    "award": ("awards", "awards", "winners"),
}
TITLE = {"paper": "paper_title", "misc": "paper_title", "book": "book_title",
         "talk": "presentation_title", "work": "work_title",
         "project": "research_project_title", "award": "award_name"}

T = {  # label key -> (en, ja)
    "authors": ("Authors", "著者"), "presenters": ("Presenters", "発表者"),
    "creators": ("Creators", "作成者"), "investigators": ("Investigators", "研究者"),
    "winners": ("Winners", "受賞者"), "venue": ("Journal / venue", "掲載誌・会議名"),
    "publisher": ("Publisher", "出版社"), "volume": ("Volume", "巻"),
    "number": ("Number", "号"), "pages": ("Pages", "ページ"),
    "total_page": ("Total pages", "総ページ数"), "date": ("Date", "日付"),
    "type": ("Type", "種類"), "refereed": ("Refereed", "査読"),
    "invited": ("Invited", "招待"), "intl": ("International", "国際"),
    "intl_journal": ("International journal", "国際誌"),
    "collab": ("International collaboration", "国際共同研究"),
    "oa": ("Open access", "オープンアクセス"), "lang": ("Languages", "言語"),
    "role": ("Role", "役割"), "range": ("Part contributed", "担当範囲"),
    "abstract": ("Description / abstract", "概要"),
    "event": ("Event", "会議名"), "location": ("Location", "開催地"),
    "promoter": ("Promoter", "主催者"), "country": ("Country", "国"),
    "period": ("Period", "期間"), "files": ("Materials", "資料"),
    "org": ("Funding body", "提供機関"), "system": ("Funding system", "制度"),
    "category": ("Category", "種目"), "inst": ("Institution", "研究機関"),
    "amount": ("Grant amount", "配分額"), "grant": ("Grant number", "課題番号"),
    "fund": ("Fund type", "資金種別"), "assoc": ("Awarding body", "授与機関"),
    "award_title": ("Award title", "受賞名"), "links": ("Links", "リンク"),
    "ids": ("Identifiers", "識別子"), "yes": ("Yes", "はい"), "no": ("No", "いいえ"),
    "details": ("Details", "詳細"), "projects": ("Research projects", "関連する研究課題"),
    "outputs": ("Related outputs", "関連する業績"), "cite": ("Cite", "引用"),
    "export": ("Export", "エクスポート"), "present": ("present", "現在"),
    "rm": ("Record on researchmap", "researchmap のレコード"),
    "back": {"paper": ("Publications", "業績"), "misc": ("Publications", "業績"),
             "book": ("Publications", "業績"), "talk": ("Talks", "講演・発表"),
             "work": ("Works", "作品等"), "project": ("Grants", "研究課題"),
             "award": ("Awards (CV)", "受賞（経歴）")},
}
VAL = {  # enum value -> (en, ja)
    "international_conference_proceedings": ("International conference proceedings", "国際会議プロシーディングス"),
    "scientific_journal": ("Journal article", "学術雑誌"),
    "symposium": ("Symposium / workshop paper", "研究会・シンポジウム資料"),
    "research_institution": ("Research institution bulletin", "研究機関紀要"),
    "meeting_report": ("Meeting report", "会議報告"), "others": ("Other", "その他"),
    "summary_international_conference": ("International conference summary", "国際会議要旨"),
    "summary_national_conference": ("National conference summary", "国内会議要旨"),
    "scholarly_book": ("Scholarly book", "学術書"),
    "contributor": ("Contributor", "分担執筆"), "joint_editor": ("Joint editor", "共編者"),
    "editor": ("Editor", "編者"), "joint_work": ("Joint work", "共著"),
    "lead": ("Lead author", "筆頭著者"),
    "public_discourse": ("Public lecture", "公開講演"),
    "oral_presentation": ("Oral presentation", "口頭発表"),
    "poster_presentation": ("Poster presentation", "ポスター発表"),
    "nominated_symposium": ("Nominated symposium / panel", "シンポジウム・パネル（指名）"),
    "public_symposium": ("Public symposium", "公開シンポジウム"),
    "invited_oral_presentation": ("Invited oral presentation", "口頭発表（招待）"),
    "keynote_oral_presentation": ("Keynote", "基調講演"),
    "database": ("Database", "データベース"), "artistic_activity": ("Artistic activity", "芸術活動"),
    "japan_society": ("Domestic society award", "国内学会等の賞"),
    "competitive_research_funding": ("Competitive research funding", "競争的資金"),
    "principal_investigator": ("Principal investigator", "研究代表者"),
    "coinvestigator": ("Co-investigator", "研究分担者"),
    "coinvestigator_not_use_grants": ("Co-investigator (no grant used)", "研究分担者（配分なし）"),
    "jpn": ("Japanese", "日本語"), "eng": ("English", "英語"),
    "JPN": ("Japan", "日本"), "HKG": ("Hong Kong", "香港"), "CAN": ("Canada", "カナダ"),
    "PRT": ("Portugal", "ポルトガル"), "AUS": ("Australia", "オーストラリア"),
}
FILTER_L = {  # list page UI
    "en": dict(q="Search keywords", year="All years", type="All types", ref="Refereed",
               inv="Invited", intl="International", sel="Selected works",
               sort="Sort", new="Newest first", old="Oldest first", count="shown",
               csv="Download CSV", bib="Download BibTeX", none="No matching items."),
    "ja": dict(q="キーワード検索", year="すべての年", type="すべての種類", ref="査読有り",
               inv="招待", intl="国際", sel="主要な業績",
               sort="並び順", new="新しい順", old="古い順", count="件を表示",
               csv="CSV をダウンロード", bib="BibTeX をダウンロード", none="該当する項目がありません。"),
}


# ---------------------------------------------------------------- helpers
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def lq(s: str) -> str:
    """Make a string safe inside a Liquid template (no braces)."""
    return s.replace("{", "&#123;").replace("}", "&#125;")


def tx(key, lg):
    v = T[key]
    return v[1 if lg == "ja" else 0]


def val(v, lg):
    if v in VAL:
        return VAL[v][1 if lg == "ja" else 0]
    return str(v).replace("_", " ").capitalize()


def norm(name: str) -> str:
    return re.sub(r"[\s,・、.]+", "", name).lower()


def plist(field, prefer="en"):
    """Complete name list (the longer of the two languages), tidied."""
    if not isinstance(field, dict):
        return []
    other = "ja" if prefer == "en" else "en"
    a, b = field.get(prefer) or [], field.get(other) or []
    out = []
    for n in (b if len(b) > len(a) else a):
        name = n.get("name", "")
        if B._JA.search(name):
            name = name.replace(", ", " ").replace(",", " ")
        if name:
            out.append(name)
    if prefer == "en" and ROMAN_READY:
        out = [en_name(n) for n in out]
    return out


ROMAN_READY = False
OWNER_EN = "Satoru Nakamura"


def en_name(name):
    """A Japanese-only name, shown on an English page with the spelling that
    person already has elsewhere in the data (never a made-up romanisation)."""
    if not B._JA.search(name):
        return name
    kind_, k = resolve(name)
    if kind_ == "owner":
        return OWNER_EN
    ent = ENT.get(k) if kind_ == "person" else None
    if ent and ent.get("en") and not B._JA.search(ent["en"]):
        return ent["en"]
    return term(name, "en")


def fdate(d, lg) -> str:
    """'2026' / '2026-04' / '2026-04-09' in the reader's language."""
    if not d or str(d).startswith("9999"):
        return ""
    p = str(d).split("-")
    mon = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    try:
        if len(p) == 1:
            return f"{p[0]}年" if lg == "ja" else p[0]
        if len(p) == 2:
            return f"{p[0]}年{int(p[1])}月" if lg == "ja" else f"{mon[int(p[1])-1]} {p[0]}"
        return (f"{p[0]}年{int(p[1])}月{int(p[2])}日" if lg == "ja"
                else f"{mon[int(p[1])-1]} {int(p[2])}, {p[0]}")
    except (ValueError, IndexError):
        return str(d)


def period(a, b, lg, open_end=True) -> str:
    x, z = fdate(a, lg), fdate(b, lg)
    if not z:
        if not open_end:
            return x
        z = tx("present", lg)
    return x if x == z else f"{x} – {z}"


def money(v, lg) -> str:
    try:
        n = f"{int(v):,}"
    except (TypeError, ValueError):
        return ""
    return f"{n}円" if lg == "ja" else f"JPY {n}"


TERM_KEYS = {"offer_organization", "system_name", "category", "institution_name",
             "publisher", "promoter", "association"}
_TERMS = None


def term(s, lg):
    """Official English name of a funding scheme, category, institution or
    publisher (scripts/term_en.json: each entry checked against the body's
    own English page). Anything not in the table stays as written."""
    global _TERMS
    if lg != "en" or not s or not B._JA.search(s):
        return s
    if _TERMS is None:
        f = Path(__file__).with_name("term_en.json")
        _TERMS = {}
        if f.exists():
            for x in json.loads(f.read_text(encoding="utf-8")):
                if x.get("en"):
                    _TERMS[x["ja"]] = x["en"]
    return _TERMS.get(s.strip(), s)


def pick(it, key, lg):
    v = B.lang(it.get(key), lg)
    return term(v, lg) if key in TERM_KEYS else v


def link_a(url, text=None, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{esc(url)}">{esc(text or url)}</a>'


def anchor_for(key):
    return "c-" + hashlib.sha1(key.encode()).hexdigest()[:8]


# --------------------------------------------------------------- registry
def _slug(kind, it, rid):
    if kind in ("paper", "misc", "book"):
        d = B.full_date(it.get("publication_date"))
        return f"{d}-{kind}-{rid}", f"/publication/{d}-{kind}-{rid}"
    if kind == "talk":
        d = B.full_date(it.get("publication_date") or it.get("from_event_date"))
        return f"{d}-talk-{rid}", f"/talks/{d}-talk-{rid}"
    pre = {"work": "works", "project": "grants", "award": "awards"}[kind]
    return f"{kind}-{rid}", f"/{pre}/{rid}"


def _sortdate(kind, it):
    f = {"work": "from_date", "project": "from_date", "award": "award_date"}.get(kind)
    if f:
        return B.full_date(it.get(f))
    return B.full_date(it.get("publication_date") or it.get("from_event_date"))


def init(Bmod):
    global B
    B = Bmod
    global ROMAN_READY
    ROMAN_READY = False
    E.clear(); BYID.clear(); SUP.clear(); ENT.clear()
    for old in B.fetch("research_projects"):
        s = old.get("x-superseded-by")
        if s and old.get("rm:id"):
            SUP[old["rm:id"]] = s["rm:id"]
    shown = {id(i) for i in B.shown_projects()}
    for kind, (mf, _, _) in KINDS.items():
        E[kind] = []
        for idx, it in enumerate(B.fetch(mf)):
            if kind == "project" and id(it) not in shown:
                continue
            rid = it.get("rm:id") or it.get("x-local-id")
            if not rid:
                rid = "p" + hashlib.sha1(B.lang(it.get(TITLE[kind]), "ja").encode()).hexdigest()[:8]
            slug, path = _slug(kind, it, rid)
            e = dict(kind=kind, it=it, id=str(rid), slug=slug, path=path,
                     date=_sortdate(kind, it), proj=[], outs=[],
                     title={lg: B.lang(it.get(TITLE[kind]), lg) or "(untitled)" for lg in ("en", "ja")})
            E[kind].append(e)
            BYID[e["id"]] = e
    _link_projects()
    _coauthors()


def aid(it):
    """Registry id of an award item."""
    return str(it.get("rm:id") or it.get("x-local-id"))


def url(e, lg):
    return ("/ja" if lg == "ja" else "") + e["path"]


def _link_projects():
    byproj = {e["id"]: e for e in E["project"]}
    def target(pid):
        return byproj.get(SUP.get(pid, pid))
    for kind in ("paper", "misc", "book", "talk", "work", "award"):
        for e in E[kind]:
            for pid in (e["it"].get("identifiers") or {}).get("rm:research_project_id", []):
                p = target(pid)
                if p and p not in e["proj"]:
                    e["proj"].append(p); p["outs"].append(e)
    for p in E["project"]:   # the reverse links the grant itself carries
        for k, v in (p["it"].get("identifiers") or {}).items():
            if k.startswith("rm:") and k.endswith("_id") and k != "rm:research_project_id":
                for oid in v:
                    o = BYID.get(oid)
                    if o and o["kind"] != "project" and p not in o["proj"]:
                        o["proj"].append(p); p["outs"].append(o)
    for p in E["project"]:
        p["outs"].sort(key=lambda o: (o["date"], o["id"]), reverse=True)


ALIAS = {}           # norm(variant) -> canonical key
LABEL = {}           # canonical key -> {"ja":..., "en":...}
EXCL = set()         # norm(name) of organisations etc.
TOK = {}             # word-order-free latin key -> canonical key


def _tok(name):
    return "t:" + " ".join(sorted(re.sub(r"[,.・]", " ", name).lower().split()))


def _load_aliases():
    ALIAS.clear(); LABEL.clear(); EXCL.clear(); TOK.clear()
    f = Path(__file__).with_name("coauthor_aliases.json")
    if not f.exists():
        return set(OWNER)
    d = json.loads(f.read_text(encoding="utf-8"))
    for g in d.get("same", []):
        k = norm(g["ja"])
        LABEL[k] = {"ja": g["ja"], "en": g.get("en") or ""}
        for n in [g["ja"], g.get("en") or ""] + g.get("also", []):
            if n:
                ALIAS[norm(n)] = k
                if not B._JA.search(n):
                    TOK[_tok(n)] = k
    EXCL.update(norm(n) for n in d.get("exclude", []))
    return set(OWNER) | {norm(n) for n in d.get("owner", [])}


def resolve(name):
    """Name as written -> (kind, key). kind is 'owner', 'skip' or 'person'."""
    k = norm(name)
    if k in OWNERS:
        return "owner", k
    if k in EXCL:
        return "skip", k
    if k in ALIAS:
        return "person", ALIAS[k]
    if B._JA.search(name):
        return "person", k
    en2ja = ENT.get("__en2ja", {})
    if k in en2ja:
        return resolve(en2ja[k]) if norm(en2ja[k]) != k else ("person", k)
    t = _tok(name)
    return "person", TOK.get(t, t)


OWNERS = set(OWNER)


def _coauthors():
    global OWNERS
    OWNERS = _load_aliases()
    # pass 1: en->ja name pairs from equal-length lists
    en2ja, pairs = {}, []
    for kind, (_, _, f) in KINDS.items():
        for e in E[kind]:
            fld = e["it"].get(f)
            if isinstance(fld, dict):
                a, b = fld.get("en") or [], fld.get("ja") or []
                if a and len(a) == len(b):
                    for x, y_ in zip(a, b):
                        if B._JA.search(y_["name"]) and not B._JA.search(x["name"]):
                            en2ja.setdefault(norm(x["name"]), y_["name"])
                            pairs.append((x["name"], y_["name"]))
    ENT["__en2ja"] = en2ja
    # word-order variants of a paired English name map to the same person
    for en_, ja_ in pairs:
        kind_, key = resolve(ja_)
        if kind_ == "person":
            TOK.setdefault(_tok(en_), key)
    for kind, (_, _, f) in KINDS.items():
        for e in E[kind]:
            seen = set()
            for lg in ("ja", "en"):
                for name in plist(e["it"].get(f), lg):
                    kind_, k = resolve(name)
                    if kind_ != "person":
                        continue
                    if not B._JA.search(name):
                        TOK.setdefault(_tok(name), k)
                    ent = ENT.setdefault(k, dict(key=k, ja="", en="", items=[]))
                    slot = "ja" if B._JA.search(name) else "en"
                    # prefer "Given Family" over "Family, Given"
                    if not ent[slot] or ("," in ent[slot] and "," not in name):
                        ent[slot] = name
                    if (k, e["id"]) not in seen:
                        seen.add((k, e["id"])); ent["items"].append(e)
    for k, ent in ENT.items():
        if k == "__en2ja":
            continue
        lab = LABEL.get(k, {})
        ent["ja"] = lab.get("ja") or ent["ja"]
        ent["en"] = lab.get("en") or ent["en"]
        ent["ja"] = ent["ja"] or ent["en"]; ent["en"] = ent["en"] or ent["ja"]
    global ROMAN_READY
    ROMAN_READY = True


def people_html(names_, lg):
    out = []
    for n in names_:
        kind_, k = resolve(n)
        if kind_ == "owner":
            out.append(f"<strong>{esc(n)}</strong>")
        elif kind_ == "person" and k in ENT:
            out.append(f'<a href="{"/ja" if lg == "ja" else ""}/coauthors/#{anchor_for(k)}">{esc(n)}</a>')
        else:
            out.append(esc(n))
    return ", ".join(out)


def _yn(v, lg):
    return tx("yes", lg) if v else tx("no", lg)


def _ids(it, lg):
    rows = []
    for k, v in (it.get("identifiers") or {}).items():
        if k.startswith("rm:") or k in ("grant_number", "national_grant_number") or not v:
            continue
        for x in v if isinstance(v, list) else [v]:
            if k == "doi":
                rows.append(link_a(f"https://doi.org/{x}", f"DOI: {x}"))
            else:
                rows.append(f"{esc(k.upper())}: {esc(x)}")
    return "<br>".join(rows)


def _links(e, lg):
    it, out = e["it"], []
    d = B.doi_url(it.get("identifiers") or {})
    if d and e["kind"] != "project":
        out.append(link_a(d, "DOI"))
    if e["kind"] == "project":
        u = B.project_url(it)
        if u:
            out.append(link_a(u, "KAKEN" if "kaken" in u else u))
    for s in it.get("see_also") or []:
        lab, u = s.get("label", ""), s.get("@id", "")
        if not u or lab.startswith("rm:") or "api.researchmap.jp" in u or lab == "kaken":
            continue
        if u not in " ".join(out):
            out.append(link_a(u))
    if it.get("x-url") and it["x-url"] not in " ".join(out):
        out.append(link_a(it["x-url"]))
    return "<br>".join(out)


def rm_url(e):
    mf, rp, _ = KINDS[e["kind"]]
    return f"https://researchmap.jp/{B.PERMALINK}/{rp}/{e['id']}" if e["it"].get("rm:id") else ""


def rows(e, lg):
    it, k = e["it"], e["kind"]
    R = []

    def add(key, v, raw=False):
        if v not in (None, "", []):
            R.append((tx(key, lg) if key in T else key, v if raw else esc(v)))

    def plabel(kind_):  # the people label for each kind
        return {"paper": "authors", "misc": "authors", "book": "authors", "talk": "presenters",
                "work": "creators", "project": "investigators", "award": "winners"}[kind_]
    f = KINDS[k][2]
    ppl = plist(it.get(f), lg)
    if ppl:
        add(plabel(k), people_html(ppl, lg), True)
    else:
        add(plabel(k), pick(it, f + "_text", lg))
    langs = ", ".join(val(x, lg) for x in it.get("languages") or [])
    if k in ("paper", "misc"):
        add("venue", pick(it, "publication_name", lg)); add("publisher", pick(it, "publisher", lg))
        add("volume", it.get("volume")); add("number", it.get("number"))
        pg = it.get("starting_page", "")
        if pg and it.get("ending_page"):
            pg += f'–{it["ending_page"]}'
        add("pages", pg); add("date", fdate(it.get("publication_date"), lg))
        ty_ = it.get("published_paper_type") or it.get("misc_type")
        add("type", val(ty_, lg) if ty_ else "")
        for key, fld in (("refereed", "referee"), ("invited", "invited"),
                         ("intl_journal", "is_international_journal"),
                         ("collab", "is_international_collaboration"), ("oa", "rm:is_open_access")):
            if fld in it:
                add(key, _yn(it[fld], lg))
        add("role", ", ".join(val(x, lg) for x in it.get("published_paper_owner_roles") or []))
        add("lang", langs); add("abstract", pick(it, "description", lg))
    elif k == "book":
        add("publisher", pick(it, "publisher", lg)); add("date", fdate(it.get("publication_date"), lg))
        add("total_page", it.get("total_page")); add("pages", it.get("rep_page"))
        add("type", val(it["book_type"], lg) if it.get("book_type") else "")
        add("role", val(it["book_owner_role"], lg) if it.get("book_owner_role") else "")
        add("range", pick(it, "book_owner_range", lg))
        if "referee" in it:
            add("refereed", _yn(it["referee"], lg))
        add("lang", langs)
    elif k == "talk":
        add("event", pick(it, "event", lg)); add("location", pick(it, "location", lg))
        add("promoter", pick(it, "promoter", lg))
        add("country", val(it["address_country"], lg) if it.get("address_country") else "")
        add("date", period(it.get("from_event_date"), it.get("to_event_date"), lg, False)
            or fdate(it.get("publication_date"), lg))
        add("type", val(it["presentation_type"], lg) if it.get("presentation_type") else "")
        if "invited" in it:
            add("invited", _yn(it["invited"], lg))
        if "is_international_presentation" in it:
            add("intl", _yn(it["is_international_presentation"], lg))
        if "is_international_collaboration" in it:
            add("collab", _yn(it["is_international_collaboration"], lg))
        add("lang", langs); add("abstract", pick(it, "description", lg))
        ds = [link_a(x["access_url"], x.get("dataset_name") or x["access_url"])
              for x in it.get("dataset") or [] if isinstance(x, dict) and x.get("access_url")] if isinstance(it.get("dataset"), list) else \
             ([link_a(it["dataset"]["access_url"], it["dataset"].get("dataset_name"))] if isinstance(it.get("dataset"), dict) and it["dataset"].get("access_url") else [])
        add("files", "<br>".join(ds), True)
    elif k == "work":
        add("period", period(it.get("from_date"), it.get("to_date"), lg), True)
        add("type", val(it["work_type"], lg) if it.get("work_type") else "")
        add("location", pick(it, "location", lg)); add("abstract", pick(it, "description", lg))
    elif k == "project":
        add("org", pick(it, "offer_organization", lg)); add("system", pick(it, "system_name", lg))
        add("category", pick(it, "category", lg)); add("inst", pick(it, "institution_name", lg))
        add("fund", val(it["fund_type"], lg) if it.get("fund_type") else "")
        add("period", period(it.get("from_date"), it.get("to_date"), lg), True)
        add("role", term(it.get("x-role"), lg) or (val(it["research_project_owner_role"], lg) if it.get("research_project_owner_role") else ""))
        a = it.get("overall_grant_amount") or {}
        if a.get("total_cost"):
            parts = [f'{money(a["total_cost"], lg)}']
            sub = [(n, a.get(c)) for n, c in ((("Direct", "直接経費"), "direct_cost"), (("Indirect", "間接経費"), "indirect_cost")) if a.get(c)]
            if sub:
                parts.append("(" + ", ".join(f'{n[1 if lg == "ja" else 0]}: {money(v, lg)}' for n, v in sub) + ")")
            add("amount", " ".join(parts))
        g = (it.get("identifiers") or {}).get("grant_number")
        add("grant", ", ".join(g) if g else "")
        add("abstract", pick(it, "description", lg))
    elif k == "award":
        add("award_title", pick(it, "award_title", lg)); add("assoc", pick(it, "association", lg))
        add("date", fdate(it.get("award_date"), lg))
        add("type", val(it["award_type"], lg) if it.get("award_type") else "")
        add("country", val(it["address_country"], lg) if it.get("address_country") else "")
        add("abstract", pick(it, "description", lg))
    add("ids", _ids(it, lg), True)
    add("links", _links(e, lg), True)
    rm = rm_url(e)
    if rm:
        add("rm", link_a(rm, "researchmap"), True)
    return R


def tlabel(o, lg):
    it = o["it"]
    ty = (it.get("published_paper_type") or it.get("misc_type") or it.get("presentation_type")
          or it.get("book_type") or it.get("work_type"))
    return val(ty, lg) if ty else T["back"][o["kind"]][1 if lg == "ja" else 0]


def _list_of(entries, lg):
    li = []
    for o in entries:
        meta = " · ".join(m for m in (tlabel(o, lg), fdate(o["date"][:7], lg)) if m)
        li.append(f'<li>{link_a(url(o, lg), o["title"][lg])} <span class="rm-meta">· {esc(meta)}</span></li>')
    return "<ul>" + "".join(li) + "</ul>"


def bibtex(e):
    """BibTeX entry (English names/titles preferred) or '' for kinds without one."""
    it, k = e["it"], e["kind"]
    if k not in ("paper", "misc", "book"):
        return ""
    def b(s):
        return re.sub(r"([&%$#_])", r"\\\1", str(s))
    ty = it.get("published_paper_type")
    typ = "book" if k == "book" else "misc" if k == "misc" else \
        "article" if ty in ("scientific_journal", "research_institution") else "inproceedings"
    f = [("author", " and ".join(plist(it.get("authors"), "en"))),
         ("title", "{" + B.lang(it.get(TITLE[k]), "en") + "}")]
    venue = B.lang(it.get("publication_name"), "en")
    if typ == "article":
        f.append(("journal", venue))
    elif typ == "inproceedings":
        f.append(("booktitle", venue))
    elif venue:
        f.append(("howpublished", venue))
    f.append(("publisher", B.lang(it.get("publisher"), "en")))
    f += [("year", B.full_date(it.get("publication_date"))[:4]), ("volume", it.get("volume")),
          ("number", it.get("number"))]
    if it.get("starting_page"):
        f.append(("pages", it["starting_page"] + (f'--{it["ending_page"]}' if it.get("ending_page") else "")))
    doi = ((it.get("identifiers") or {}).get("doi") or [""])[0]
    f += [("doi", doi), ("url", B.link(it))]
    body = ",\n".join(f"  {n} = {{{b(v) if n not in ('title', 'doi', 'url') else v}}}" for n, v in f if v and v != "{}")
    return f"@{typ}{{rm{e['id']},\n{body}\n}}\n"


def _jsonld(e, lg):
    it, k = e["it"], e["kind"]
    people = [{"@type": "Person", "name": n} for n in plist(it.get(KINDS[k][2]), lg)]
    d = {"@context": "https://schema.org", "name": e["title"][lg], "inLanguage": lg,
         "url": B.PROFILE["website"] + url(e, lg)}
    desc = pick(it, "description", lg)
    if desc:
        d["description"] = desc
    if k in ("paper", "misc"):
        d.update({"@type": "ScholarlyArticle", "author": people,
                  "datePublished": B.full_date(it.get("publication_date"))[:10]})
        v = pick(it, "publication_name", lg)
        if v:
            d["isPartOf"] = {"@type": "Periodical", "name": v}
        if B.doi_url(it.get("identifiers") or {}):
            d["sameAs"] = B.doi_url(it["identifiers"])
    elif k == "book":
        d.update({"@type": "Book", "author": people, "publisher": pick(it, "publisher", lg),
                  "datePublished": B.full_date(it.get("publication_date"))[:10]})
    elif k == "talk":
        loc = pick(it, "location", lg) or pick(it, "event", lg)
        d.update({"@type": "Event", "name": pick(it, "event", lg) or e["title"][lg],
                  "startDate": it.get("from_event_date") or B.full_date(it.get("publication_date")),
                  "performer": people, "workPerformed": {"@type": "CreativeWork", "name": e["title"][lg]},
                  "location": {"@type": "Place", "name": loc}})
        if it.get("to_event_date"):
            d["endDate"] = it["to_event_date"]
    elif k == "work":
        d.update({"@type": "CreativeWork", "creator": people, "dateCreated": it.get("from_date", "")})
        if B.link(it):
            d["sameAs"] = B.link(it)
    elif k == "project":
        d.update({"@type": "MonetaryGrant", "funder": {"@type": "Organization", "name": pick(it, "offer_organization", lg)},
                  "startDate": it.get("from_date", "")})
        a = (it.get("overall_grant_amount") or {}).get("total_cost")
        if a:
            d["amount"] = {"@type": "MonetaryAmount", "currency": "JPY", "value": int(a)}
        if B.project_url(it):
            d["sameAs"] = B.project_url(it)
    else:
        d.update({"@type": "CreativeWork", "creator": people, "dateCreated": it.get("award_date", "")})
    d = {k_: v for k_, v in d.items() if v not in ("", [], None)}
    return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def _citation_meta(e, lg):
    it = e["it"]
    if e["kind"] not in ("paper", "book", "misc"):
        return ""
    m = [("citation_title", e["title"][lg])]
    m += [("citation_author", n) for n in plist(it.get("authors"), lg)]
    dt = B.full_date(it.get("publication_date"))
    m.append(("citation_publication_date", dt.replace("-", "/")))
    venue = pick(it, "publication_name", lg)
    ty = it.get("published_paper_type")
    if venue:
        m.append(("citation_conference_title" if ty in ("international_conference_proceedings", "symposium")
                  else "citation_journal_title", venue))
    for n, v in (("citation_volume", it.get("volume")), ("citation_issue", it.get("number")),
                 ("citation_firstpage", it.get("starting_page")), ("citation_lastpage", it.get("ending_page")),
                 ("citation_publisher", pick(it, "publisher", lg)),
                 ("citation_language", {"jpn": "ja", "eng": "en"}.get((it.get("languages") or [""])[0], "")),
                 ("citation_doi", ((it.get("identifiers") or {}).get("doi") or [""])[0]),
                 ("citation_isbn", ((it.get("identifiers") or {}).get("isbn") or [""])[0])):
        if v:
            m.append((n, v))
    return "".join(f'<meta name="{n}" content="{esc(v)}">' for n, v in m)


def render(e, lg, md=False):
    """(front matter dict, HTML body) of one detail page."""
    other = "en" if lg == "ja" else "ja"
    head = _jsonld(e, lg) + _citation_meta(e, lg) + \
        f'<link rel="alternate" hreflang="{other}" href="{B.PROFILE["website"]}{url(e, other)}">'
    dl = "".join(f"<dt>{esc(a)}</dt><dd>{b}</dd>" for a, b in rows(e, lg))
    pre = "/ja" if lg == "ja" else ""
    listp = {"paper": "publications", "misc": "publications", "book": "publications",
             "talk": "talks", "work": "works", "project": "grants"}.get(e["kind"])
    back = (f'<a href="{pre}/{listp}/">← {esc(T["back"][e["kind"]][1 if lg == "ja" else 0])}</a>'
            if listp else f'<a href="{pre}/cv/#awards">← {esc(T["back"]["award"][1 if lg == "ja" else 0])}</a>')
    parts = [f'<div class="rm-detail"><p class="rm-meta">{back}</p>']
    if e["kind"] == "work" and e["it"].get("x-thumbnail"):
        parts.append(f'<p><img class="rm-detail-img" src="{esc(e["it"]["x-thumbnail"])}" alt="{esc(e["title"][lg])}"></p>')
    parts.append(f"<dl class=\"rm-dl\">{dl}</dl>")
    if e["proj"]:
        parts.append(f'<h2>{esc(tx("projects", lg))}</h2>' + _list_of(e["proj"], lg))
    if e["outs"]:
        parts.append(f'<h2>{esc(tx("outputs", lg))} ({len(e["outs"])})</h2>' + _list_of(e["outs"], lg))
    if e["kind"] in ("paper", "misc", "book"):
        cite = e.get("cite_ja" if lg == "ja" else "cite", "")
        bib = bibtex(e)
        parts.append(f'<h2>{esc(tx("cite", lg))}</h2><p>{cite}</p>')
        parts.append(f'<pre class="rm-bib"><code>{esc(bib)}</code></pre>')
        parts.append(f'<p class="rm-meta">{esc(tx("export", lg))}: '
                     f'<a href="/files/export/bib/{e["slug"]}.bib" download>BibTeX (.bib)</a> · '
                     f'<a href="/files/export/json/{e["slug"]}.json" download>JSON</a></p>')
    else:
        parts.append(f'<p class="rm-meta">{esc(tx("export", lg))}: '
                     f'<a href="/files/export/json/{e["slug"]}.json" download>JSON</a></p>')
    parts.append("</div>")
    body = lq("".join(parts))
    if md:   # collection files (.md) are run through kramdown
        body = "{::nomarkdown}\n" + body + "\n{:/nomarkdown}"
    ppl = ", ".join(plist(e["it"].get(KINDS[e["kind"]][2]), lg)[:6])
    desc = " — ".join(x for x in (ppl, pick(e["it"], "publication_name", lg) or pick(e["it"], "event", lg)
                                  or pick(e["it"], "publisher", lg), fdate(e["date"], lg)) if x)
    front = {"layout": "detail", "title": e["title"][lg], "lang": lg, "description": desc,
             "alt_url": url(e, other), "head_html": head, "kind": e["kind"]}
    return front, body


# ------------------------------------------------------------------- lists
def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip().lower()


def _li(e, lg, inner, tags):
    it = e["it"]
    a = {"year": e["date"][:4], "date": e["date"], "type": tags.get("type", ""),
         "ref": "1" if it.get("referee") else "", "inv": "1" if it.get("invited") else "",
         "intl": "1" if (it.get("is_international_presentation") or it.get("is_international_journal")) else "",
         "sel": "1" if it.get("major_achievement") else "",
         "text": _text(inner + " " + " ".join(plist(it.get(KINDS[e["kind"]][2]), "en") + plist(it.get(KINDS[e["kind"]][2]), "ja")) + " " + e["title"]["en"] + " " + e["title"]["ja"])}
    at = " ".join(f'data-{k}="{esc(v)}"' for k, v in a.items() if v != "" or k in ("year", "date"))
    cls = tags.get("cls", "")
    return f'<li class="rm-item{cls}" {at}>{inner}</li>'


def _detail_badge(e, lg):
    return f'<a class="rm-link" href="{esc(url(e, lg))}">{esc(tx("details", lg))}</a>'


def _toolbar(lg, flags, csvs):
    F = FILTER_L[lg]
    chk = "".join(f'<label class="rm-chk" data-flag="{k}"><input type="checkbox" data-f="{k}"> {F[k]}</label>' for k in flags)
    dl = " · ".join(f'<a href="{u}" download>{F[n]}</a>' for n, u in csvs)
    return (f'<div class="rm-filter" role="search"><input type="search" data-f="q" placeholder="{F["q"]}" aria-label="{F["q"]}">'
            f'<select data-f="year" aria-label="{F["year"]}"><option value="">{F["year"]}</option></select>'
            f'<select data-f="type" aria-label="{F["type"]}"><option value="">{F["type"]}</option></select>'
            f'{chk}<select data-f="sort" aria-label="{F["sort"]}"><option value="new">{F["new"]}</option><option value="old">{F["old"]}</option></select>'
            f'<span class="rm-count" aria-live="polite"><b data-n></b>/<span data-total></span> {F["count"]}</span>'
            f'<span class="rm-dl-links">{dl}</span></div>')


def _grouped(items, lg, render_li, sec_id="", sec_title=""):
    """Year-grouped list; items = [(entry, li_html)] already sorted newest first."""
    out, last = [], None
    groups = {}
    for e, li in items:
        groups.setdefault(e["date"][:4], []).append(li)
    h = f'<section class="rm-sec" id="{sec_id}">' + (f'<h2 class="rm-h2">{sec_title}</h2>' if sec_title else "")
    body = "".join(f'<div class="rm-yg" data-year="{y}"><h3 class="rm-year" id="y{y}">{y}</h3><ol class="rm-list">{"".join(l)}</ol></div>'
                   for y, l in groups.items())
    return h + body + "</section>"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sorted(kind):
    return sorted(E[kind], key=lambda e: (e["date"], e["id"]), reverse=True)


def lists():
    for lg in ("en", "ja"):
        F = FILTER_L[lg]
        # --- publications
        secs = []
        names_ = {"en": {"book": "Books", "paper": "Papers", "misc": "Articles &amp; Reports"},
                  "ja": {"book": "書籍等出版物", "paper": "論文", "misc": "MISC"}}[lg]
        toc = []
        for kind in ("book", "paper", "misc"):
            lis = []
            for e in _sorted(kind):
                cite = e.get("cite_ja" if lg == "ja" else "cite", "")
                cite = cite.replace(e["title"][lg], f'<a href="{esc(url(e, lg))}">{e["title"][lg]}</a>', 1) if e["title"][lg] in cite else cite
                it = e["it"]
                tl = tlabel(e, lg)
                badge = _detail_badge(e, lg)
                d = B.doi_url(it.get("identifiers") or {})
                inner = f'{cite} {badge}' + (f' <a class="rm-link" href="{esc(d)}">DOI</a>' if d else "")
                lis.append((e, _li(e, lg, inner, {"type": tl})))
            toc.append(f'<a href="#{kind}s">{names_[kind]} <span>{len(lis)}</span></a>')
            secs.append(_grouped(lis, lg, None, f"{kind}s", names_[kind]))
        csvs = [("csv", "/files/export/publications.csv"), ("bib", "/files/export/publications.bib")]
        _write(B.ROOT / "_includes" / "gen" / f"list-pubs-{lg}.html",
               lq('<div data-rm-list>' + _toolbar(lg, ["ref", "sel"], csvs) + '<nav class="rm-toc">' + "".join(toc) + "</nav>"
                  + "".join(secs) + f'<p class="rm-empty" hidden>{F["none"]}</p></div>'
                  + '<script src="/assets/js/rm-list.js" defer></script>'))
        # --- talks
        lis = []
        for e in _sorted("talk"):
            it = e["it"]
            pt = val(it["presentation_type"], lg) if it.get("presentation_type") else ""
            who = ", ".join(plist(it.get("presenters"), lg)) or pick(it, "presenters_text", lg)
            ven = pick(it, "event", lg)
            inner = (f'<span class="rm-title">{link_a(url(e, lg), e["title"][lg])}</span><br>'
                     f'<span class="rm-meta">{esc(who)}{" — " + esc(ven) if ven else ""}, {esc(fdate(e["date"], lg))}</span>'
                     + (f'<span class="rm-badge">{esc(pt)}</span>' if pt else "")
                     + (f'<span class="rm-badge">{esc(tx("invited", lg))}</span>' if it.get("invited") and "invited" not in it.get("presentation_type", "") else ""))
            lis.append((e, _li(e, lg, inner, {"type": pt})))
        years = sorted({e["date"][:4] for e, _ in lis}, reverse=True)
        counts = {y_: sum(1 for e, _ in lis if e["date"][:4] == y_) for y_ in years}
        toc = "".join(f'<a href="#y{y_}">{y_} <span>{counts[y_]}</span></a>' for y_ in years)
        _write(B.ROOT / "_includes" / "gen" / f"list-talks-{lg}.html",
               lq('<div data-rm-list>' + _toolbar(lg, ["inv", "intl", "sel"], [("csv", "/files/export/talks.csv")])
                  + f'<nav class="rm-toc">{toc}</nav>' + _grouped(lis, lg, None) + f'<p class="rm-empty" hidden>{F["none"]}</p></div>'
                  + '<script src="/assets/js/rm-list.js" defer></script>'))
        # --- works
        lis = []
        for e in sorted(E["work"], key=lambda e: (e["date"], e["id"]), reverse=True):
            it = e["it"]
            th = it.get("x-thumbnail")
            who = ", ".join(plist(it.get("creators"), lg)) or pick(it, "creators_text", lg)
            inner = ((f'<a class="rm-thumb" href="{esc(url(e, lg))}" tabindex="-1" aria-hidden="true"><img src="{esc(th)}" alt="{esc(e["title"][lg])}" loading="lazy" width="160" height="100"></a>' if th else "")
                     + f'<div class="rm-body"><span class="rm-title">{link_a(url(e, lg), e["title"][lg])}</span>'
                       + (f' {link_a(B.link(it), "↗", "rm-link")}' if B.link(it) else "")
                       + f'<br><span class="rm-meta">{esc(who)} · {esc(period(it.get("from_date"), it.get("to_date"), lg))}</span></div>')
            lis.append((e, _li(e, lg, inner, {"cls": " rm-item--thumb" if th else "",
                                              "type": val(it["work_type"], lg) if it.get("work_type") else ""})))
        _write(B.ROOT / "_includes" / "gen" / f"list-works-{lg}.html",
               lq('<div data-rm-list>' + _toolbar(lg, ["sel"], [("csv", "/files/export/works.csv")]) + _grouped(lis, lg, None)
                  + f'<p class="rm-empty" hidden>{F["none"]}</p></div><script src="/assets/js/rm-list.js" defer></script>'))
        # --- grants
        lis = []
        for e in sorted(E["project"], key=lambda e: (e["date"], e["id"]), reverse=True):
            it = e["it"]
            u = B.project_url(it)
            meta = " · ".join(x for x in (pick(it, "offer_organization", lg), pick(it, "system_name", lg) or pick(it, "category", lg),
                                          period(it.get("from_date"), it.get("to_date"), lg)) if x)
            inv = ", ".join(plist(it.get("investigators"), lg))
            inner = (f'<span class="rm-title">{link_a(url(e, lg), e["title"][lg])}</span>'
                     + (f' {link_a(u, "KAKEN" if "kaken" in u else "↗", "rm-link")}' if u else "")
                     + f'<br><span class="rm-meta">{esc(meta)}</span>'
                     + (f'<br><span class="rm-meta">{esc(tx("investigators", lg))}: {esc(inv)}</span>' if inv else ""))
            lis.append((e, _li(e, lg, inner, {"type": pick(it, "system_name", lg)})))
        _write(B.ROOT / "_includes" / "gen" / f"list-grants-{lg}.html",
               lq('<div data-rm-list>' + _toolbar(lg, [], [("csv", "/files/export/grants.csv")]) + _grouped(lis, lg, None)
                  + f'<p class="rm-empty" hidden>{F["none"]}</p></div><script src="/assets/js/rm-list.js" defer></script>'))


# -------------------------------------------------------------- coauthors
def coauthors_pages():
    for lg in ("en", "ja"):
        pre = "/ja" if lg == "ja" else ""
        ents = sorted((v for k, v in ENT.items() if k != "__en2ja"),
                      key=lambda v: (-len(v["items"]), v[lg].lower()))
        total = len(ents)
        lis = []
        for v in ents:
            kc = {}
            for o in v["items"]:
                kc[o["kind"]] = kc.get(o["kind"], 0) + 1
            kinds = " · ".join(f'{T["back"][k][1 if lg == "ja" else 0]} {n}' for k, n in sorted(kc.items()))
            items = sorted(v["items"], key=lambda o: (o["date"], o["id"]), reverse=True)
            inner = (f'<details id="{anchor_for(v["key"])}"><summary><span class="rm-title">{esc(v[lg])}</span> '
                     f'<span class="rm-badge">{len(items)}</span> <span class="rm-meta">{esc(kinds)}</span></summary>'
                     + _list_of(items, lg) + "</details>")
            lis.append(f'<li class="rm-item" data-text="{esc(_text(v["ja"] + " " + v["en"]))}">{inner}</li>')
        F = FILTER_L[lg]
        intro = ("共著者・共同発表者・共同研究者（論文・発表・作品・研究課題・受賞に名前が載っている人）を、名前ごとに集計しました。"
                 "本人は除いています。件数の多い順です。" if lg == "ja" else
                 "Co-authors, co-presenters and co-investigators across papers, talks, works, grants and awards, aggregated by name (the site owner excluded), most frequent first.")
        body = (lq(f'<p>{intro}</p><div data-rm-list><div class="rm-filter"><input type="search" data-f="q" placeholder="{F["q"]}" aria-label="{F["q"]}">'
                f'<span class="rm-count"><b data-n></b>/<span data-total></span> {"名" if lg == "ja" else "people"}</span></div>'
                f'<ol class="rm-list">{"".join(lis)}</ol><p class="rm-empty" hidden>{F["none"]}</p></div>'
                '<script src="/assets/js/rm-list.js" defer></script>'))
        front = {"layout": "archive", "title": "共同研究者" if lg == "ja" else "Co-researchers",
                 "permalink": f"{pre}/coauthors/", "author_profile": True, "lang": lg}
        B.write_md(B.ROOT / "_pages" / ("ja/coauthors.html" if lg == "ja" else "coauthors.html"), front, body)
    print(f"  coauthors: {len(ents)} people")


# ----------------------------------------------------------------- exports
def exports():
    root = B.ROOT / "files" / "export"
    if root.exists():
        shutil.rmtree(root)
    (root / "bib").mkdir(parents=True); (root / "json").mkdir(parents=True)
    allbib = []
    for kind, ents in E.items():
        for e in ents:
            clean = {k: v for k, v in e["it"].items() if not k.startswith("x-") and k != "@reverse"}
            (root / "json" / f"{e['slug']}.json").write_text(
                json.dumps(clean, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            b = bibtex(e)
            if b:
                (root / "bib" / f"{e['slug']}.bib").write_text(b, encoding="utf-8")
                allbib.append((e, b))
    allbib.sort(key=lambda x: (x[0]["date"], x[0]["id"]), reverse=True)
    (root / "publications.bib").write_text("\n".join(b for _, b in allbib), encoding="utf-8")

    def out(name, kinds, header, fn):
        with open(root / name, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow(header)
            for e in sorted((x for k in kinds for x in E[k]), key=lambda e: (e["date"], e["id"]), reverse=True):
                w.writerow(fn(e))
    site = B.PROFILE["website"]
    def common(e):
        it = e["it"]
        return [e["kind"], e["date"], e["title"]["en"], e["title"]["ja"],
                "; ".join(plist(it.get(KINDS[e["kind"]][2]), "en")), "; ".join(plist(it.get(KINDS[e["kind"]][2]), "ja"))]
    ch = ["type", "date", "title_en", "title_ja", "people_en", "people_ja"]
    out("publications.csv", ("book", "paper", "misc"), ch + ["venue", "publisher", "volume", "number", "pages", "refereed", "doi", "page_url"],
        lambda e: common(e) + [B.lang(e["it"].get("publication_name"), "en"), B.lang(e["it"].get("publisher"), "en"),
                               e["it"].get("volume", ""), e["it"].get("number", ""),
                               "-".join(x for x in (e["it"].get("starting_page"), e["it"].get("ending_page")) if x),
                               "yes" if e["it"].get("referee") else "", B.doi_url(e["it"].get("identifiers") or {}), site + url(e, "en")])
    out("talks.csv", ("talk",), ch + ["event", "location", "from", "to", "presentation_type", "invited", "international", "page_url"],
        lambda e: common(e) + [B.lang(e["it"].get("event"), "en"), B.lang(e["it"].get("location"), "en"),
                               e["it"].get("from_event_date", ""), e["it"].get("to_event_date", ""), e["it"].get("presentation_type", ""),
                               "yes" if e["it"].get("invited") else "", "yes" if e["it"].get("is_international_presentation") else "", site + url(e, "en")])
    out("works.csv", ("work",), ch + ["from", "to", "url", "page_url"],
        lambda e: common(e) + [e["it"].get("from_date", ""), B.end_date(e["it"].get("to_date")), B.link(e["it"]), site + url(e, "en")])
    out("grants.csv", ("project",), ch + ["funding_body", "system", "category", "from", "to", "total_cost_jpy", "grant_number", "url", "page_url"],
        lambda e: common(e) + [B.lang(e["it"].get("offer_organization"), "en"), B.lang(e["it"].get("system_name"), "en"), B.lang(e["it"].get("category"), "en"),
                               e["it"].get("from_date", ""), B.end_date(e["it"].get("to_date")),
                               (e["it"].get("overall_grant_amount") or {}).get("total_cost", ""),
                               ", ".join((e["it"].get("identifiers") or {}).get("grant_number", [])), B.project_url(e["it"]), site + url(e, "en")])


def finish():
    """Everything not written inline by build_site: ja pages, en work/grant/
    award pages, lists, coauthors, exports."""
    gen = B.ROOT / "_pages" / "gen"
    if gen.exists():
        shutil.rmtree(gen)
    n = 0
    for lg in ("en", "ja"):
        (gen / lg).mkdir(parents=True, exist_ok=True)
    for kind, ents in E.items():
        for e in ents:
            for lg in ("en", "ja"):
                if lg == "en" and kind in ("paper", "misc", "book", "talk"):
                    continue   # written by build_site into _publications / _talks
                front, body = render(e, lg)
                front["permalink"] = url(e, lg)
                B.write_md(gen / lg / f"{e['slug']}.html", front, body)
                n += 1
    lists(); coauthors_pages(); exports()
    print(f"  detail pages: {n} generated + {sum(len(E[k]) for k in ('paper','misc','book','talk'))} in collections")
