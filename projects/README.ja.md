# プロジェクト

中村 覚が参画した主なプロジェクトと、それぞれでの職名・役割。
個々の作品の期間・規模は `master/works.json`、研究費は `master/research_projects.json` にある。
このフォルダには、それらの一覧に無いこと（職名、担った役割、どの作品がどのプロジェクトから生まれたか）を書く。

英語版（正本）: [README.md](README.md)

## 直し方

ここの Markdown が正本。直したら次を実行する。

```
python3 scripts/build_projects.py
```

頁（`/projects/`、`/ja/projects/`）と、ダウンロード用の JSON
（`files/export/projects.json`、`files/export/projects.ja.json`。[JSON Resume](https://jsonresume.org/schema/) の形式）ができる。

各ファイルの冒頭に欄（`name`、`organization`、`position`、`start`、`end`、`url`、`status`、`notes`）を置き、
本文は 4 つの節にする。`## 役割`（文章）、`## 作品`（`- [名前](URL) 年-月`）、
`## 関連する研究費`（`- 課題 | 期間 | 課題番号 | 立場`）、`## 根拠`（自由に書く）。

## プロジェクト

- [東京大学デジタルアーカイブズ構築事業](utokyo-digital-archives.ja.md)
- [東洋文庫の研究データベース](toyo-bunko.ja.md)
- [国立歴史民俗博物館](rekihaku.ja.md)
- [国立国会図書館](ndl.ja.md)
- [Cultural Japan](cultural-japan.ja.md)
- [デジタル源氏物語](digital-genji.ja.md)
