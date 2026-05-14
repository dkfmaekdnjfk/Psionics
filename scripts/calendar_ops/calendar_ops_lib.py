from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")

NOTE_PATTERN = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+?)\s*$")
TASK_DEFAULT_LINE_PATTERN = re.compile(r"^- (?:`)?([a-zA-Z_][a-zA-Z0-9_]*)(?:`)?:\s*(.+?)\s*$")


@dataclass
class Event:
    calendar: str
    title: str
    start_utc: datetime
    end_utc: datetime
    start_kst: datetime
    end_kst: datetime
    location: str
    notes: str
    all_day: bool
    note_meta: dict[str, str]


@dataclass
class TaskStats:
    predicted_hours: float
    median_hours: float
    ewma_hours: float
    sample_count: int
    confidence: str


def parse_iso_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_kst(value: datetime) -> datetime:
    return value.astimezone(KST)


def parse_note_meta(notes: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in notes.splitlines():
        m = NOTE_PATTERN.match(line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        meta[key] = val
    return meta


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9가-힣\s_-]", "", text).strip().lower()
    slug = re.sub(r"[\s_]+", "-", normalized)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled-task"


def default_repeat_key_from_title(title: str) -> str | None:
    lower_title = title.lower()
    if "neuroai off" in lower_title:
        return "neuroai-미팅-오프라인"
    if "com neuro" in lower_title:
        return "com-neuro-스터디"
    if "독서클럽" in title:
        return "독서클럽"
    if "송미팅" in title:
        return "송미팅"
    return None


def load_events(events_path: Path) -> list[Event]:
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    rows: list[Event] = []
    for item in payload.get("events", []):
        start_utc = parse_iso_utc(item["start"])
        end_utc = parse_iso_utc(item["end"])
        notes = item.get("notes") or ""
        rows.append(
            Event(
                calendar=item.get("calendar", ""),
                title=item.get("title", "(untitled)"),
                start_utc=start_utc,
                end_utc=end_utc,
                start_kst=to_kst(start_utc),
                end_kst=to_kst(end_utc),
                location=item.get("location", ""),
                notes=notes,
                all_day=bool(item.get("allDay", False)),
                note_meta=parse_note_meta(notes),
            )
        )
    rows.sort(key=lambda e: e.start_kst)
    return rows


def parse_frontmatter_markdown(md_text: str) -> tuple[dict[str, Any], str]:
    if not md_text.startswith("---\n"):
        return {}, md_text

    parts = md_text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, md_text

    fm_text = parts[0][4:]
    body = parts[1]
    data: dict[str, Any] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip()
    return data, body


def parse_float(meta: dict[str, str], key: str, default: float | None = None) -> float | None:
    raw = meta.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def parse_int(meta: dict[str, str], key: str, default: int | None = None) -> int | None:
    raw = meta.get(key)
    if raw is None:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def ewma(values: list[float], alpha: float = 0.4) -> float:
    acc = values[0]
    for val in values[1:]:
        acc = alpha * val + (1 - alpha) * acc
    return acc


def calc_task_stats(hours: list[float], sample_count: int | None = None) -> TaskStats:
    if not hours:
        return TaskStats(predicted_hours=1.0, median_hours=1.0, ewma_hours=1.0, sample_count=0, confidence="low")

    med = float(statistics.median(hours))
    recent = ewma(hours)
    predicted = round(0.6 * recent + 0.4 * med, 2)

    count = sample_count if sample_count is not None else len(hours)
    if count >= 8:
        conf = "high"
    elif count >= 3:
        conf = "medium"
    else:
        conf = "low"

    return TaskStats(
        predicted_hours=predicted,
        median_hours=round(med, 2),
        ewma_hours=round(recent, 2),
        sample_count=count,
        confidence=conf,
    )


def parse_records_from_task_doc(md_text: str) -> tuple[list[float], set[str]]:
    lines = md_text.splitlines()
    reading_table = False
    hours: list[float] = []
    sample_days: set[str] = set()

    for line in lines:
        if line.strip() == "## Records":
            reading_table = True
            continue
        if reading_table and line.startswith("## "):
            break
        if not reading_table or "|" not in line:
            continue
        if line.strip().startswith("| date") or line.strip().startswith("|---"):
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 6:
            continue
        date_raw = cols[0]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_raw):
            sample_days.add(date_raw)
        actual = cols[5]
        planned = cols[4]
        candidate = actual if actual else planned
        try:
            if candidate:
                hours.append(float(candidate))
        except ValueError:
            continue
    return hours, sample_days


def parse_defaults_from_task_doc(md_text: str) -> dict[str, str]:
    lines = md_text.splitlines()
    reading_defaults = False
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped == "## Defaults":
            reading_defaults = True
            continue
        if reading_defaults and stripped.startswith("## "):
            break
        if not reading_defaults:
            continue
        m = TASK_DEFAULT_LINE_PATTERN.match(stripped)
        if not m:
            continue
        values[m.group(1).strip()] = m.group(2).strip()
    return values


def ensure_task_doc(
    task_path: Path,
    task_title: str,
    repeat_key: str,
    default_priority: int,
    default_eta: float,
    event: Event,
    today_str: str,
) -> tuple[TaskStats, bool]:
    unique_row_key = f"{event.start_kst.isoformat()}::{event.title}"

    if task_path.exists():
        existing = task_path.read_text(encoding="utf-8")
    else:
        existing = ""

    history_hours, sample_days = parse_records_from_task_doc(existing)
    event_actual = parse_float(event.note_meta, "actual_hours")
    event_planned = max((event.end_kst - event.start_kst).total_seconds() / 3600, 0.0)

    records_table = [
        "| date | event_title | start_kst | end_kst | planned_hours | actual_hours | note | row_key |",
        "|---|---|---|---|---:|---:|---|---|",
    ]

    existing_rows: set[str] = set()
    if existing:
        for line in existing.splitlines():
            stripped = line.strip()
            if stripped.startswith("| date ") or stripped.startswith("|---"):
                continue
            if line.count("|") < 8:
                continue
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 8 and cols[7]:
                existing_rows.add(cols[7])
                records_table.append(line)

    if unique_row_key not in existing_rows:
        if event_actual and event_actual > 0:
            history_hours.append(event_actual)
        elif event_planned > 0:
            history_hours.append(round(event_planned, 2))
        sample_days.add(event.start_kst.date().isoformat())

    stats = calc_task_stats(history_hours, sample_count=len(sample_days))

    changed = False
    if unique_row_key not in existing_rows:
        records_table.append(
            "| {date} | {title} | {start} | {end} | {planned:.2f} | {actual} | {note} | {row} |".format(
                date=event.start_kst.date().isoformat(),
                title=event.title.replace("|", "/"),
                start=event.start_kst.strftime("%Y-%m-%d %H:%M"),
                end=event.end_kst.strftime("%Y-%m-%d %H:%M"),
                planned=event_planned,
                actual=(f"{event_actual:.2f}" if event_actual else ""),
                note=(event.note_meta.get("note", "") or "").replace("|", "/"),
                row=unique_row_key,
            )
        )
        changed = True

    created_value = today_str
    if task_path.exists() and existing:
        created_value = parse_frontmatter_markdown(existing)[0].get("created", today_str)

    frontmatter = "\n".join(
        [
            "---",
            "type: entity",
            "subtype: task",
            "tags: [schedule, productivity]",
            f"created: {created_value}",
            f"updated: {today_str}",
            'sources: ["output/calendar/events.json"]',
            f"confidence: {stats.confidence}",
            "---",
            "",
        ]
    )

    doc = [
        frontmatter,
        f"# {task_title}",
        "",
        f"캘린더 반복 업무 문서입니다. 반복 키는 `{repeat_key}` 입니다.",
        "",
        "## Defaults",
        f"- `priority`: {default_priority}",
        f"- `eta_hours`: {default_eta:.2f}",
        f"- `repeat_key`: {repeat_key}",
        "",
        "## Estimates",
        f"- `predicted_hours`: {stats.predicted_hours:.2f}",
        f"- `median_hours`: {stats.median_hours:.2f}",
        f"- `ewma_hours`: {stats.ewma_hours:.2f}",
        f"- `sample_count`: {stats.sample_count}",
        f"- `confidence`: {stats.confidence}",
        "",
        "## Records",
        *records_table,
        "",
        "## Usage",
        "- 완료 후 캘린더 notes 또는 이 문서에 `actual_hours`를 기록하면 ETA 예측이 개선됩니다.",
        "- 캘린더 notes 예시: `priority: 4`, `eta_hours: 2.5`, `repeat_key: com-neuro-study`, `actual_hours: 2.2`",
        "",
    ]

    new_text = "\n".join(doc)
    if not task_path.exists() or new_text != existing:
        task_path.write_text(new_text, encoding="utf-8")
        changed = True

    return stats, changed


def score_event_session(priority: int, days_left: int, session_hours: float) -> float:
    urgency = max(0, 30 - days_left)
    return round(priority * 0.5 + urgency * 0.35 + session_hours * 0.15, 4)
