---
permalink: /ja/
title: "中村 覚"
author_profile: true
lang: ja
header:
  og_image: og.png
---

{% assign rm = site.data.researchmap %}
{% assign a = rm.affiliations | first %}
**{{ a.institutionJa }} {{ a.jobJa }}**

{{ rm.profileJa }}

## 業績の概要

{% include rm-glance.html lang="ja" %}

## 研究分野・キーワード

{% for r in rm.researchAreas %}{{ r.fieldJa }}{% endfor %}<br>
{{ rm.keywordsJa | join: "、" }}

## リンク

- 業績の全体: [researchmap](https://researchmap.jp/nakamura.satoru)
- ソフトウェア: [GitHub](https://github.com/nakamura196)
- 技術ブログ: [ldas.jp](https://ldas.jp/ja/)

{% include rm-source.html lang="ja" %}
