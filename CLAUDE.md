# Psionics — LLM Wiki

Your personal knowledge base. You are the **editor** of this wiki.

## Core Rules (7)
1. Never modify `raw/` — read-only
2. All wiki pages must have YAML frontmatter
3. Link related concepts with `[[wikilinks]]`
4. After every query, update the wiki (dual-output rule)
5. After every operation, append one line to `wiki/log.md`
6. Keep `wiki/index.md` always up to date
7. Mark uncertain information with `confidence: low`

## Directory Structure
```
raw/         → your source documents (read-only)
wiki/
  concepts/  → concept pages
  entities/  → people · tools · papers · models
  sources/   → one summary per raw source
  summaries/ → cross-source synthesis (after 2+ sources)
  queries/   → valuable query results worth keeping
  index.md   → full table of contents (always current)
  log.md     → operation history (append-only)
  overview.md→ big-picture synthesis
output/      → blog drafts, reports, slides
```

## Operation Triggers
| Trigger | Operation |
|---------|-----------|
| "add / summarize / ingest" | INGEST |
| "explain / tell me / what's the difference?" | QUERY |
| "lint / health check" | LINT |
| "why did this change?" | REFLECT |

## Detailed Reference
- Workflow details: `.claude/skills/karpathy-wiki/references/operations.md`
- Frontmatter templates & tags: `wiki/SCHEMA.md`
