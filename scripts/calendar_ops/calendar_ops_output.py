from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CALENDAR_BLOCK_START = "<!-- CALENDAR_OPS_START -->"
CALENDAR_BLOCK_END = "<!-- CALENDAR_OPS_END -->"
DEFAULT_DAILY_ROUTINE_ROWS = [
    {"time": "00:00-01:00", "type": "routine", "detail": "취침", "status": "planned"},
    {"time": "08:00", "type": "routine", "detail": "기상", "status": "planned"},
    {"time": "09:30-10:00", "type": "routine", "detail": "지하철 이동 중 30분 작업", "status": "planned"},
    {"time": "12:00-13:00", "type": "routine", "detail": "점심 식사", "status": "planned"},
    {"time": "18:00+", "type": "routine", "detail": "퇴근/야근(택1로 수정)", "status": "planned"},
]
DAILY_LOG_ALLOWED_TYPES = {"focus", "work", "admin", "routine", "waste", "break", "incident"}
TABLE_SEPARATOR_PATTERN = re.compile(r"^:?-{3,}:?$")


def write_source_snapshot(source_path: Path, events: list[Any], today_str: str) -> None:
    lines = [
        "---",
        "type: source",
        'source: "output/calendar/events.json"',
        f'original_title: "calendar export {today_str}"',
        "tags: [calendar, schedule, productivity]",
        f"created: {today_str}",
        "confidence: high",
        "---",
        "",
        f"# calendar-{today_str}",
        "",
        "캘린더에서 오늘 기준 향후 30일 일정을 스냅샷한 문서입니다.",
        "",
        "## Events",
    ]
    for ev in events:
        lines.append(
            f"- {ev.start_kst.strftime('%Y-%m-%d %H:%M')} ~ {ev.end_kst.strftime('%H:%M')} | {ev.title} | {ev.calendar}"
        )
    lines.append("")
    source_path.write_text("\n".join(lines), encoding="utf-8")


def write_daily_brief(
    query_path: Path,
    items: list[dict[str, Any]],
    today_str: str,
    daily_log_slug: str,
    routine_slug: str,
) -> None:
    lines = [
        "---",
        "type: query",
        "tags: [calendar, schedule, productivity]",
        f"created: {today_str}",
        f"updated: {today_str}",
        "sources: [\"output/calendar/events.json\"]",
        "confidence: medium",
        "---",
        "",
        f"# schedule-brief-{today_str}",
        "",
        "향후 30일 업무를 회차(수업/미팅 1건) 기준으로 정렬한 브리핑입니다.",
        "",
        "## Priority Queue",
        "| rank | date | task | days_left | priority | predicted_hours | total_hours_30d | score | task_doc | mapped_by | confidence |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]

    for idx, row in enumerate(items, start=1):
        lines.append(
            (
                "| {rank} | {date} | {task} | {days} | {priority} | {eta:.2f} | {total:.2f} | "
                "{score:.2f} | [[{task_slug}]] | {matched_by} | {conf:.2f} |"
            ).format(
                rank=idx,
                date=row["start_date"],
                task=row["title"].replace("|", "/"),
                days=row["days_left"],
                priority=row["priority"],
                eta=row["predicted_hours"],
                total=row.get("total_hours_30d", row["predicted_hours"]),
                score=row["score"],
                task_slug=row["task_slug"],
                matched_by=row.get("matched_by", ""),
                conf=float(row.get("match_confidence", 0.0)),
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- 점수식(회차 기준): `0.5*priority + 0.35*urgency(30-days_left) + 0.15*predicted_hours`",
            "- `predicted_hours`: 해당 회차(이벤트 1건)의 예상 소요시간",
            "- `total_hours_30d`: 같은 task의 향후 30일 예상 소요시간 합계(보조 지표)",
            "- 미매핑 이벤트는 `schedule-triage-YYYY-MM-DD.md`에서 확인/분류합니다.",
            f"- 일일 시간기록: [[{daily_log_slug}]]",
            f"- 고정 생활 루틴: [[{routine_slug}]]",
            "",
        ]
    )
    query_path.write_text("\n".join(lines), encoding="utf-8")


def update_index(index_path: Path, today_str: str, task_count: int) -> None:
    text = index_path.read_text(encoding="utf-8")
    block = "\n".join(
        [
            CALENDAR_BLOCK_START,
            "## 🗓️ 일정 관리 (Calendar Ops)",
            "",
            f"- [[calendar-{today_str}]] — 오늘 기준 30일 일정 스냅샷",
            f"- [[schedule-brief-{today_str}]] — 우선순위 브리핑",
            f"- [[schedule-triage-{today_str}]] — 미매핑/취소 triage 큐",
            f"- [[daily-{today_str}]] — 일일 시간기록",
            "- [[personal-routine]] — 고정 루틴",
            f"- [[tasks-index]] — 업무 문서 인덱스 (현재 {task_count}개)",
            CALENDAR_BLOCK_END,
        ]
    )

    if CALENDAR_BLOCK_START in text and CALENDAR_BLOCK_END in text:
        text = re.sub(
            re.escape(CALENDAR_BLOCK_START) + r".*?" + re.escape(CALENDAR_BLOCK_END),
            block,
            text,
            flags=re.DOTALL,
        )
    else:
        text = text.rstrip() + "\n\n---\n\n" + block + "\n"

    index_path.write_text(text, encoding="utf-8")


def ensure_tasks_index(tasks_index_path: Path, task_ids: list[str], today_str: str) -> None:
    lines = [
        "---",
        "type: summary",
        "topic: \"calendar tasks index\"",
        "sources: [\"wiki/entities/tasks/catalog.json\"]",
        "tags: [calendar, schedule, productivity]",
        f"created: {today_str}",
        f"updated: {today_str}",
        "confidence: high",
        "---",
        "",
        "# tasks-index",
        "",
        "업무별 문서 목록입니다.",
        "",
        "## Tasks",
    ]
    for slug in sorted(set(task_ids)):
        lines.append(f"- [[{slug}]]")
    lines.append("")
    tasks_index_path.write_text("\n".join(lines), encoding="utf-8")


def write_triage_report(
    triage_path: Path,
    unmapped_rows: list[dict[str, Any]],
    canceled_rows: list[dict[str, Any]],
    today_str: str,
) -> None:
    lines = [
        "---",
        "type: query",
        "tags: [calendar, schedule, triage]",
        f"created: {today_str}",
        f"updated: {today_str}",
        "sources: [\"output/calendar/events.json\", \"output/calendar/unmapped_events.json\"]",
        "confidence: medium",
        "---",
        "",
        f"# schedule-triage-{today_str}",
        "",
        "자동 매핑에 실패한 일정과 취소 처리된 일정을 정리한 큐입니다.",
        "",
        "## Unmapped",
        "| date | calendar | title | reason | suggestions |",
        "|---|---|---|---|---|",
    ]

    for row in unmapped_rows:
        suggestion_text = ", ".join(
            [f"{s['task_id']} ({s['score']})" for s in row.get("suggestions", [])]
        )
        lines.append(
            "| {date} | {calendar} | {title} | {reason} | {suggestions} |".format(
                date=row["start_date"],
                calendar=row["calendar"].replace("|", "/"),
                title=row["title"].replace("|", "/"),
                reason=row.get("reason", "").replace("|", "/"),
                suggestions=suggestion_text.replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Canceled",
            "| date | calendar | title |",
            "|---|---|---|",
        ]
    )
    for row in canceled_rows:
        lines.append(
            "| {date} | {calendar} | {title} |".format(
                date=row["start_date"],
                calendar=row["calendar"].replace("|", "/"),
                title=row["title"].replace("|", "/"),
            )
        )
    lines.append("")
    triage_path.write_text("\n".join(lines), encoding="utf-8")


def write_unmapped_events_json(
    out_path: Path,
    unmapped_rows: list[dict[str, Any]],
    canceled_rows: list[dict[str, Any]],
    today_str: str,
) -> None:
    payload = {
        "generatedAt": today_str,
        "unmappedCount": len(unmapped_rows),
        "canceledCount": len(canceled_rows),
        "unmapped": unmapped_rows,
        "canceled": canceled_rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_personal_routine(routine_path: Path, today_str: str) -> None:
    if routine_path.exists():
        return
    lines = [
        "---",
        "type: summary",
        "topic: \"personal routine\"",
        "sources: [\"user-input\"]",
        "tags: [routine, productivity, schedule]",
        f"created: {today_str}",
        f"updated: {today_str}",
        "confidence: high",
        "---",
        "",
        "# personal-routine",
        "",
        "일정 계획/복기를 위한 고정 생활 루틴 프로필.",
        "",
        "## Baseline",
        "- 기상: 08:00",
        "- 출근 완료 목표: 10:00",
        "- 지하철 작업: 09:30-10:00 (30분)",
        "- 점심: 12:00-13:00",
        "- 퇴근 기준: 18:00 (야근 가능)",
        "- 취침: 00:00-01:00",
        "",
    ]
    routine_path.parent.mkdir(parents=True, exist_ok=True)
    routine_path.write_text("\n".join(lines), encoding="utf-8")


def ensure_daily_log(
    daily_log_path: Path,
    today_str: str,
    routine_slug: str,
    seed_rows: list[dict[str, str]] | None = None,
) -> None:
    if daily_log_path.exists():
        return

    rows = [*DEFAULT_DAILY_ROUTINE_ROWS, *(seed_rows or [])]
    lines = [
        "---",
        "type: note",
        "tags: [daily-log, schedule, productivity]",
        f"created: {today_str}",
        f"updated: {today_str}",
        "sources: [\"user-input\", \"output/calendar/events.json\"]",
        "confidence: medium",
        "---",
        "",
        f"# daily-{today_str}",
        "",
        f"하루 시간대별 실행 기록. 루틴 기준은 [[{routine_slug}]].",
        "",
        "## Time Log",
        "| time | type | detail | status |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {time} | {type} | {detail} | {status} |".format(
                time=row.get("time", ""),
                type=row.get("type", ""),
                detail=row.get("detail", "").replace("|", "/"),
                status=row.get("status", "planned"),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "- 완료 후 `status`를 `done`으로 변경하고 실제 내용을 보강합니다.",
            "- `type` 권장 enum: `focus`, `work`, `admin`, `routine`, `waste`, `break`, `incident`",
            "",
        ]
    )
    daily_log_path.parent.mkdir(parents=True, exist_ok=True)
    daily_log_path.write_text("\n".join(lines), encoding="utf-8")


def validate_daily_log_types(daily_log_path: Path) -> list[dict[str, str]]:
    if not daily_log_path.exists():
        return []

    invalid_rows: list[dict[str, str]] = []
    lines = daily_log_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---") or stripped.startswith("| time"):
            continue
        cols = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cols) < 4:
            continue
        if all(re.fullmatch(r":?-{3,}:?", col or "") for col in cols[:4]):
            continue
        row_type = cols[1]
        if row_type not in DAILY_LOG_ALLOWED_TYPES:
            invalid_rows.append(
                {
                    "time": cols[0],
                    "type": row_type,
                    "detail": cols[2],
                }
            )
    return invalid_rows


def _parse_time_start_minutes(time_text: str) -> int | None:
    value = time_text.strip()
    if not value:
        return None
    if value.endswith("+"):
        value = value[:-1]
    if "-" in value:
        value = value.split("-", 1)[0]
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    if hh > 24 or mm > 59:
        return None
    if hh == 24 and mm != 0:
        return None
    return hh * 60 + mm


def _extract_daily_rows(daily_log_path: Path) -> list[dict[str, str]]:
    if not daily_log_path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line_no, line in enumerate(daily_log_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cols = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cols) < 4:
            continue
        if cols[0].lower() == "time" and cols[1].lower() == "type":
            continue
        if all(TABLE_SEPARATOR_PATTERN.fullmatch(c or "") for c in cols[:4]):
            continue
        rows.append(
            {
                "line_no": str(line_no),
                "time": cols[0],
                "type": cols[1],
                "detail": cols[2],
                "status": cols[3],
            }
        )
    return rows


def validate_daily_log_order(daily_log_path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    rows = _extract_daily_rows(daily_log_path)
    prev_minutes: int | None = None
    prev_time = ""
    for row in rows:
        current_minutes = _parse_time_start_minutes(row["time"])
        if current_minutes is None:
            continue
        if prev_minutes is not None and current_minutes < prev_minutes:
            issues.append(
                {
                    "line_no": row["line_no"],
                    "time": row["time"],
                    "prev_time": prev_time,
                }
            )
        prev_minutes = current_minutes
        prev_time = row["time"]
    return issues


def validate_evening_status(daily_log_path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    rows = _extract_daily_rows(daily_log_path)
    evening_row: dict[str, str] | None = None
    for row in rows:
        if row["time"].startswith("18:00+"):
            evening_row = row
            break
    if not evening_row:
        return issues

    detail = evening_row["detail"].strip()
    status = evening_row["status"].strip().lower()
    normalized_detail = detail.replace(" ", "")
    if normalized_detail not in {"퇴근", "야근", "퇴근/야근(택1로수정)"}:
        issues.append(
            {
                "line_no": evening_row["line_no"],
                "reason": "evening detail must be '퇴근' or '야근'",
                "value": detail,
            }
        )

    late_rows = [
        row
        for row in rows
        if (_parse_time_start_minutes(row["time"]) or -1) >= 18 * 60 and row["time"] != "18:00+"
    ]
    has_done_late_work = any(
        (row["status"].strip().lower() == "done") and (row["type"].strip() in {"focus", "work", "admin", "waste"})
        for row in late_rows
    )
    if detail == "퇴근" and has_done_late_work:
        issues.append(
            {
                "line_no": evening_row["line_no"],
                "reason": "late work exists after 18:00 but evening detail is 퇴근",
                "value": detail,
            }
        )
    if status == "planned" and has_done_late_work:
        issues.append(
            {
                "line_no": evening_row["line_no"],
                "reason": "18:00+ row is still planned while later done rows exist",
                "value": detail,
            }
        )
    if normalized_detail == "퇴근/야근(택1로수정)" and status == "done":
        issues.append(
            {
                "line_no": evening_row["line_no"],
                "reason": "18:00+ detail must be finalized to 퇴근 or 야근 when status is done",
                "value": detail,
            }
        )
    return issues


def _daily_date_from_path(daily_log_path: Path) -> datetime.date | None:
    m = re.search(r"daily-(\d{4}-\d{2}-\d{2})\.md$", daily_log_path.name)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y-%m-%d").date()


def _parse_time_end_minutes(time_text: str) -> int | None:
    value = time_text.strip()
    if not value:
        return None
    if value.endswith("+"):
        return _parse_time_start_minutes(value)
    if "-" in value:
        end_text = value.split("-", 1)[1]
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", end_text)
        if not m:
            return None
        hh = int(m.group(1))
        mm = int(m.group(2))
        if hh > 24 or mm > 59:
            return None
        if hh == 24 and mm != 0:
            return None
        return hh * 60 + mm
    return _parse_time_start_minutes(value)


def validate_past_planned(daily_log_path: Path, now_kst: datetime) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    rows = _extract_daily_rows(daily_log_path)
    daily_date = _daily_date_from_path(daily_log_path)
    if daily_date is None:
        return issues

    now_date = now_kst.date()
    now_minutes = now_kst.hour * 60 + now_kst.minute

    for row in rows:
        if row["status"].strip().lower() != "planned":
            continue

        if daily_date < now_date:
            issues.append(
                {
                    "line_no": row["line_no"],
                    "time": row["time"],
                    "detail": row["detail"],
                    "reason": "planned row exists in a past day",
                }
            )
            continue

        if daily_date > now_date:
            continue

        end_minutes = _parse_time_end_minutes(row["time"])
        if end_minutes is not None and end_minutes <= now_minutes:
            issues.append(
                {
                    "line_no": row["line_no"],
                    "time": row["time"],
                    "detail": row["detail"],
                    "reason": "planned row exists in a past time slot",
                }
            )
    return issues


def append_log(log_path: Path, today_str: str, mapped_count: int, unmapped_count: int) -> None:
    entry = (
        f"## [{today_str}] query | 캘린더 30일 업무 브리핑 자동 생성 — "
        f"mapped {mapped_count}, unmapped {unmapped_count}, schedule-brief/triage 갱신"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")
