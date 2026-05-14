# Psionics

Personal knowledge base framework for Claude Code. Obsidian-compatible markdown wiki with auto-ingest, concept linking, and query filing.

Based on [Andrej Karpathy's LLM Wiki pattern](https://x.com/karpathy/status/1862449670231720047) — raw sources are ingested once, compiled into a living wiki, and kept current rather than re-derived on every query.

## How it works

1. Drop sources into `raw/` (articles, papers, notes, PDFs)
2. Tell Claude to ingest — it extracts concepts, entities, and synthesis into `wiki/`
3. Ask questions — Claude reads the wiki and files valuable answers back in
4. The knowledge base compounds over time

## Directory structure

```
raw/         → your source documents (read-only, curated by you)
wiki/
  concepts/  → one page per concept
  entities/  → people, papers, tools, models
  sources/   → one summary per raw source
  summaries/ → cross-source synthesis (after 2+ sources on a topic)
  queries/   → valuable query results worth keeping
  index.md   → full table of contents
  log.md     → append-only operation history
  overview.md→ big-picture synthesis
output/      → blog drafts, reports, slides
```

## Getting started

### Prerequisites
- [Claude Code](https://claude.ai/code) CLI

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/Psionics.git
cd Psionics
claude  # opens Claude Code in this directory
```

Claude will automatically load `CLAUDE.md` and operate as your wiki editor.

### Usage

| You say | Claude does |
|---------|-------------|
| "add this article" / "ingest raw/paper.md" | INGEST — extracts concepts, updates wiki |
| "what do we know about X?" | QUERY — reads wiki, synthesizes answer |
| "lint the wiki" | LINT — finds orphans, broken links, gaps |
| "why did X change?" | REFLECT — traces concept evolution in log |

## Key features

- **Auto-ingest hook** — when you stop a session, Claude silently checks for new `raw/` files and processes them
- **Drift detection** — on session start, alerts you to unprocessed sources
- **FSRS fields** — optional spaced-repetition metadata on concept pages
- **Obsidian-compatible** — `[[wikilinks]]`, YAML frontmatter, standard markdown

## Customization

Edit `wiki/SCHEMA.md` to adjust:
- Frontmatter fields per page type
- Tag taxonomy for your domain
- Naming conventions

Edit `CLAUDE.md` to change Claude's behavior as editor.

## License

MIT
