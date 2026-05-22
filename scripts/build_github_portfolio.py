#!/usr/bin/env python3
"""Generate _portfolio/*.md from the user's GitHub repositories.

Pulls public, non-fork, non-archived repos via the GitHub REST API, ranks them
by stars (then recency), and writes the top N as academicpages portfolio items
that link straight to GitHub.

Re-runnable: clears and regenerates _portfolio on every run.

Auth: uses GITHUB_TOKEN / GH_TOKEN from the environment if present (required in
CI to avoid the low unauthenticated rate limit); works unauthenticated locally.

Usage:
    python3 scripts/build_github_portfolio.py
    GH_USER=nakamura196 PORTFOLIO_TOP=12 python3 scripts/build_github_portfolio.py
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "nakamura196")
TOP = int(os.environ.get("PORTFOLIO_TOP", "12"))
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_portfolio"


def gh_get(url: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "site-builder"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = gh_get(
            f"https://api.github.com/users/{USER}/repos"
            f"?per_page=100&page={page}&type=owner&sort=updated"
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def main():
    repos = fetch_repos()
    repos = [r for r in repos
             if not r.get("fork") and not r.get("archived") and not r.get("private")
             and r.get("name") not in (USER, f"{USER}.github.io")]
    repos.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("updated_at", "")),
               reverse=True)
    top = repos[:TOP]

    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.md"):
        f.unlink()

    for i, r in enumerate(top):
        name = r["name"]
        desc = (r.get("description") or "").strip()
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or ""
        meta = " · ".join(x for x in [(f"★ {stars}" if stars else ""), lang] if x)
        excerpt = desc + (f"<br/><small>{meta}</small>" if meta else "")
        front = {
            "title": name,
            "excerpt": excerpt,
            "collection": "portfolio",
            "link": r["html_url"],
        }
        lines = ["---"]
        for k, v in front.items():
            lines.append(f"{k}: {yaml_str(v)}")
        lines.append("---")
        body = desc
        home = (r.get("homepage") or "").strip()
        if home and home.rstrip("/") != r["html_url"].rstrip("/"):
            body += f"\n\n[Live site]({home})"
        body += f"\n\n[View on GitHub]({r['html_url']})"
        (OUT / f"{i:02d}-{name}.md").write_text(
            "\n".join(lines) + "\n\n" + body + "\n", encoding="utf-8")

    print(f"  _portfolio: {len(top)} repos "
          f"(top stars: {', '.join(str(r.get('stargazers_count', 0)) for r in top[:5])})")


if __name__ == "__main__":
    main()
