# Wiki Schema

> Detailed rules referenced by CLAUDE.md. Read only when needed.

---

## Frontmatter Templates

### concepts/
```yaml
---
type: concept
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["raw/category/filename.md"]
related: ["[[other concept]]"]
confidence: high | medium | low
# FSRS review fields (auto-managed — do not edit manually)
review_enabled: true
stability: null
difficulty: 5.0
last_reviewed: null
next_review: null
review_count: 0
---
```
Body: one-line definition → intuitive explanation → key formulas/algorithms → related concepts

### entities/
```yaml
---
type: entity
subtype: person | paper | model | tool | dataset | book | channel
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["raw/category/filename.md"]
related: ["[[related concept]]"]
---
```
Body: one-line intro → background/key contributions → main connections → related links

### sources/
> **1:1 summary** of a raw source. One page per source document.

```yaml
---
type: source
source: "raw/category/filename.md"
original_title: "Original Title"
tags: [...]
created: YYYY-MM-DD
confidence: high | medium | low
---
```
Body: 3-line summary → 3–5 key insights → structure of the source → related wiki pages

### summaries/
> **Cross-source synthesis** by topic. Create after 2+ related sources accumulate.

```yaml
---
type: summary
topic: "Topic Name"
sources: ["wiki/sources/file1.md", "wiki/sources/file2.md"]
tags: [...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
---
```
Body: one-line topic definition → key arguments/flow → comparison across sources → open questions → related concepts

---

## INGEST — 5 Steps

1. **Extract** — pull key concepts, entities, claims
2. **Classify** — decide which page types are needed
   - `sources/` : 1:1 summary of this source
   - `concepts/` : one page per extracted concept
   - `entities/` : people, papers, tools, models, books, channels
   - `summaries/` : cross-source synthesis (2+ sources on same topic)
3. **Connect** — find `[[links]]` to existing wiki pages
4. **Integrate** — create/update pages (1 source typically touches 5–15 pages)
5. **Review** — update index.md, append to log.md

---

## LINT Checklist

- [ ] Broken `[[links]]` (wikilinks pointing to missing files)
- [ ] Orphan pages (no inbound links)
- [ ] Pages with `confidence: low`
- [ ] Pages not updated in 90+ days
- [ ] Pages missing from index.md
- [ ] Contradicting claims across pages

---

## Tag Guide

Adapt tags to your domain. Default suggestions:

| Tag | Domain |
|-----|--------|
| `math` | linear algebra, calculus, general math |
| `statistics` | probability, Bayesian inference |
| `ml` | machine learning, deep learning |
| `llm` | large language models, prompting, agents |
| `reading` | book notes, reading summaries |
| `blog` | blog ideas, drafts, published posts |
| `research` | hypotheses, papers, experiments |

---

## log.md Format

```
## [YYYY-MM-DD] ingest | Source Title
## [YYYY-MM-DD] query | Question summary
## [YYYY-MM-DD] lint | Health check summary
## [YYYY-MM-DD] reflect | Changed concept name
## [YYYY-MM-DD] schema | Schema change description
```

---

## File Naming

```
raw/      → YYYY-MM-DD-title-slug.md  (or any format you prefer)
wiki/     → english-slug.md           (no dates — LLM updates continuously)
output/   → YYYY-MM-DD-task-name.md
```

### wiki/ filename rules
- All filenames in **English**
- If the concept has a Wikipedia article, use that title (e.g., `receptive-field`, `kl-divergence`)
- Acronyms stay uppercase (e.g., `glm-neural-encoding`, `kl-divergence`)
- Word separator: hyphen (`-`), lowercase by default

---

## Token Efficiency

- Session start: the SessionStart hook auto-detects raw/ drift
- At 80% context, run `/compact` and restart
- For long sessions, `/compact` every ~40 messages is recommended
- Keep SCHEMA.md separate — read only when needed, not on every turn
