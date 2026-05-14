from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CatalogTask:
    task_id: str
    title: str
    default_priority: int
    default_eta_hours: float
    status: str
    aliases: list[str]


@dataclass
class MatchResult:
    mapped: bool
    task_id: str | None
    method: str
    confidence: float
    suggestions: list[dict[str, Any]]
    fingerprint: str
    reason: str


def normalize_text(text: str) -> str:
    value = text.lower().strip()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^0-9a-z가-힣]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_canceled_event(title: str, note_meta: dict[str, str]) -> bool:
    status = (note_meta.get("status") or "").strip().lower()
    if status in {"canceled", "cancelled", "skip"}:
        return True

    normalized = normalize_text(title)
    if normalized.endswith(" x") or " 취소" in normalized or "cancel" in normalized:
        return True
    return False


def event_fingerprint(calendar_name: str, title: str) -> str:
    return f"{normalize_text(calendar_name)}|{normalize_text(title)}"


def load_catalog(catalog_path: Path) -> dict[str, CatalogTask]:
    if not catalog_path.exists():
        return {}

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    by_id: dict[str, CatalogTask] = {}
    for item in tasks:
        task_id = str(item.get("task_id", "")).strip()
        if not task_id:
            continue
        by_id[task_id] = CatalogTask(
            task_id=task_id,
            title=str(item.get("title", task_id)),
            default_priority=max(1, min(5, int(item.get("default_priority", 3)))),
            default_eta_hours=float(item.get("default_eta_hours", 1.0)),
            status=str(item.get("status", "active")),
            aliases=[str(v).strip() for v in item.get("aliases", []) if str(v).strip()],
        )
    return by_id


def load_links(links_path: Path) -> dict[str, dict[str, Any]]:
    if not links_path.exists():
        return {}
    payload = json.loads(links_path.read_text(encoding="utf-8"))
    return payload.get("links", {})


def save_links(links_path: Path, links: dict[str, dict[str, Any]]) -> None:
    links_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "links": links}
    links_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def active_task_ids(catalog: dict[str, CatalogTask]) -> list[str]:
    return sorted([task_id for task_id, task in catalog.items() if task.status == "active"])


def _alias_score(title_norm: str, alias_norm: str) -> float:
    if not alias_norm:
        return 0.0
    if alias_norm == title_norm:
        return 1.0
    if alias_norm in title_norm:
        return min(0.95, 0.55 + len(alias_norm) / max(1, len(title_norm)))
    if title_norm in alias_norm:
        return 0.51

    title_tokens = set(title_norm.split())
    alias_tokens = set(alias_norm.split())
    if not title_tokens or not alias_tokens:
        return 0.0

    overlap = len(title_tokens & alias_tokens)
    union = len(title_tokens | alias_tokens)
    jaccard = overlap / union
    return 0.45 * jaccard


def _suggest_from_aliases(title: str, catalog: dict[str, CatalogTask]) -> list[dict[str, Any]]:
    title_norm = normalize_text(title)
    scores: list[tuple[str, float, str]] = []
    for task in catalog.values():
        if task.status != "active":
            continue
        best_score = 0.0
        best_alias = ""
        for alias in [task.title, *task.aliases]:
            alias_norm = normalize_text(alias)
            score = _alias_score(title_norm, alias_norm)
            if score > best_score:
                best_score = score
                best_alias = alias
        if best_score > 0:
            scores.append((task.task_id, best_score, best_alias))

    scores.sort(key=lambda row: row[1], reverse=True)
    return [
        {"task_id": task_id, "score": round(score, 3), "matched_alias": alias}
        for task_id, score, alias in scores[:3]
    ]


def match_event_to_task(
    calendar_name: str,
    title: str,
    note_meta: dict[str, str],
    catalog: dict[str, CatalogTask],
    links: dict[str, dict[str, Any]],
) -> MatchResult:
    fingerprint = event_fingerprint(calendar_name, title)

    note_task_id = (note_meta.get("task_id") or "").strip()
    if note_task_id and note_task_id in catalog and catalog[note_task_id].status == "active":
        return MatchResult(
            mapped=True,
            task_id=note_task_id,
            method="note_task_id",
            confidence=1.0,
            suggestions=[],
            fingerprint=fingerprint,
            reason="task_id provided in notes",
        )

    link_hit = links.get(fingerprint)
    if link_hit:
        linked_task_id = str(link_hit.get("task_id", "")).strip()
        if linked_task_id in catalog and catalog[linked_task_id].status == "active":
            return MatchResult(
                mapped=True,
                task_id=linked_task_id,
                method="links_cache",
                confidence=float(link_hit.get("confidence", 0.9)),
                suggestions=[],
                fingerprint=fingerprint,
                reason="cached event-title mapping",
            )

    suggestions = _suggest_from_aliases(title, catalog)
    if suggestions and suggestions[0]["score"] >= 0.72:
        winner = suggestions[0]
        return MatchResult(
            mapped=True,
            task_id=winner["task_id"],
            method="alias_match",
            confidence=max(0.72, float(winner["score"])),
            suggestions=suggestions,
            fingerprint=fingerprint,
            reason=f"alias matched: {winner['matched_alias']}",
        )

    return MatchResult(
        mapped=False,
        task_id=None,
        method="unmapped",
        confidence=0.0,
        suggestions=suggestions,
        fingerprint=fingerprint,
        reason="no reliable mapping found",
    )
