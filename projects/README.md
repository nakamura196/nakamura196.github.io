# Projects

Major projects Satoru Nakamura has taken part in, with his position and role in each.
Periods and sizes of individual outputs are in `master/works.json`; grants are in `master/research_projects.json`.
This folder records what those lists do not: the position held, the role taken, and which outputs came from which project.

Japanese version: [README.ja.md](README.ja.md)

## How to edit

The Markdown files here are the source. Edit them, then run:

```
python3 scripts/build_projects.py
```

This writes the pages (`/projects/`, `/ja/projects/`) and the JSON download
(`files/export/projects.json`, `files/export/projects.ja.json`, in [JSON Resume](https://jsonresume.org/schema/) format).

Each file has front matter (`name`, `organization`, `position`, `start`, `end`, `url`, `status`, `notes`)
and four sections: `## Role` (a paragraph), `## Outputs` (`- [Name](url) YYYY-MM`),
`## Related grants` (`- Title | period | number | position`) and `## Evidence` (free text).
The Japanese file uses the same sections in Japanese (`役割`, `作品`, `関連する研究費`, `根拠`).

## Projects

- [UTokyo Digital Archives Project](utokyo-digital-archives.md)
- [Toyo Bunko research databases](toyo-bunko.md)
- [National Museum of Japanese History](rekihaku.md)
- [National Diet Library](ndl.md)
- [Cultural Japan](cultural-japan.md)
- [Digital Tale of Genji](digital-genji.md)
