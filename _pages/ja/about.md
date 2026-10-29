---
permalink: /ja/
title: "中村 覚"
author_profile: true
lang: ja
header:
  og_image: og.png
---

{% assign rm = site.data.researchmap %}
{{ rm.profileJa }}

## 業績の概要

{% include rm-glance.html lang="ja" %}

## 研究分野・キーワード

{% for r in rm.researchAreas %}{{ r.fieldJa }}{% endfor %}<br>
{{ rm.keywordsJa | join: "、" }}

## リンク

- researchmap: [nakamura.satoru](https://researchmap.jp/nakamura.satoru)
- ORCID: [0000-0001-8245-7925](https://orcid.org/0000-0001-8245-7925)
- ソフトウェア: [GitHub](https://github.com/nakamura196)
- 技術ブログ: [ldas.jp](https://ldas.jp/ja/)

{% include rm-source.html lang="ja" %}
