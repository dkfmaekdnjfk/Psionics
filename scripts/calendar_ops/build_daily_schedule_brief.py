#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from calendar_ops_lib import (
    KST,
    ensure_task_doc,
    load_events,
    parse_float,
    parse_int,
    score_event_session,
)
from calendar_ops_output import (
    append_log,
    ensure_daily_log,
    ensure_personal_routine,
    ensure_tasks_index,
    update_index,
    validate_daily_log_types,
    validate_daily_log_order,
    validate_evening_status,
    validate_past_planned,
    write_daily_brief,
    write_source_snapshot,
    write_triage_report,
    write_unmapped_events_json,
)
from calendar_task_registry import (
    active_task_ids,
    is_canceled_event,
    load_catalog,
    load_links,
    match_event_to_task,
    save_links,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build wiki schedule brief from Calendar export")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--events-file", type=Path, default=Path("output/calendar/events.json"))
    parser.add_argument("--window-days", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.repo_root.resolve()

    events_path = (root / args.events_file).resolve()
    wiki_dir = root / "wiki"
    tasks_dir = wiki_dir / "entities" / "tasks"
    logs_dir = wiki_dir / "logs"
    routine_path = wiki_dir / "overview" / "personal-routine.md"
    catalog_path = tasks_dir / "catalog.json"
    links_path = root / "output" / "calendar" / "event_task_links.json"

    if not events_path.exists():
        raise FileNotFoundError(f"events file not found: {events_path}")

    now = datetime.now(KST)
    today = now.date()
    cutoff = now + timedelta(days=args.window_days)
    today_str = today.isoformat()

    events = load_events(events_path)
    in_window = [
        ev
        for ev in events
        if now <= ev.start_kst <= cutoff
        and not ev.all_day
        and "공휴일" not in ev.calendar
        and "생일" not in ev.calendar
    ]

    tasks_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "sources").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "queries").mkdir(parents=True, exist_ok=True)
    (root / "output" / "calendar").mkdir(parents=True, exist_ok=True)
    ensure_personal_routine(routine_path, today_str)

    daily_log_slug = f"daily-{today_str}"
    daily_log_path = logs_dir / f"{daily_log_slug}.md"
    ensure_daily_log(
        daily_log_path=daily_log_path,
        today_str=today_str,
        routine_slug="personal-routine",
    )
    invalid_daily_types = validate_daily_log_types(daily_log_path)
    for row in invalid_daily_types:
        print(
            "WARNING: invalid daily log type '{type}' at {time} in {path} (detail: {detail})".format(
                type=row["type"] or "(empty)",
                time=row["time"] or "(no-time)",
                path=daily_log_path,
                detail=row["detail"] or "(empty)",
            )
        )
    invalid_daily_order = validate_daily_log_order(daily_log_path)
    for row in invalid_daily_order:
        print(
            "WARNING: daily log time order issue at line {line_no} in {path} "
            "(previous: {prev_time}, current: {time})".format(
                line_no=row["line_no"],
                path=daily_log_path,
                prev_time=row["prev_time"] or "(none)",
                time=row["time"] or "(none)",
            )
        )
    evening_issues = validate_evening_status(daily_log_path)
    for row in evening_issues:
        print(
            "WARNING: evening status issue at line {line_no} in {path} "
            "({reason}; value: {value})".format(
                line_no=row["line_no"],
                path=daily_log_path,
                reason=row["reason"],
                value=row["value"] or "(empty)",
            )
        )
    past_planned_issues = validate_past_planned(daily_log_path, now)
    if past_planned_issues:
        for row in past_planned_issues:
            print(
                "ERROR: past-planned issue at line {line_no} in {path} "
                "({reason}; time: {time}; detail: {detail})".format(
                    line_no=row["line_no"],
                    path=daily_log_path,
                    reason=row["reason"],
                    time=row["time"],
                    detail=row["detail"],
                )
            )
        raise RuntimeError("Guardrail violation: planned rows cannot remain in past time slots.")

    catalog = load_catalog(catalog_path)
    links = load_links(links_path)
    if not catalog:
        raise RuntimeError(f"task catalog is missing or empty: {catalog_path}")

    mapped_rows: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    touched_task_ids: list[str] = []
    unmapped: list[dict[str, Any]] = []
    skipped_canceled: list[dict[str, Any]] = []

    for ev in in_window:
        if is_canceled_event(ev.title, ev.note_meta):
            skipped_canceled.append(
                {
                    "title": ev.title,
                    "calendar": ev.calendar,
                    "start_date": ev.start_kst.strftime("%Y-%m-%d %H:%M"),
                }
            )
            continue

        match = match_event_to_task(
            calendar_name=ev.calendar,
            title=ev.title,
            note_meta=ev.note_meta,
            catalog=catalog,
            links=links,
        )

        if not match.mapped or not match.task_id:
            unmapped.append(
                {
                    "title": ev.title,
                    "calendar": ev.calendar,
                    "start_date": ev.start_kst.strftime("%Y-%m-%d %H:%M"),
                    "reason": match.reason,
                    "fingerprint": match.fingerprint,
                    "suggestions": match.suggestions,
                }
            )
            continue

        task = catalog[match.task_id]
        task_path = tasks_dir / f"{task.task_id}.md"

        default_priority = parse_int(ev.note_meta, "priority", task.default_priority) or task.default_priority
        default_priority = max(1, min(5, default_priority))
        default_eta = parse_float(ev.note_meta, "eta_hours", task.default_eta_hours)
        if default_eta is None:
            default_eta = task.default_eta_hours

        stats, _ = ensure_task_doc(
            task_path=task_path,
            task_title=task.title,
            repeat_key=task.task_id,
            default_priority=default_priority,
            default_eta=default_eta,
            event=ev,
            today_str=today_str,
        )

        days_left = (ev.start_kst.date() - today).days
        predicted_hours = stats.predicted_hours if stats.sample_count else float(default_eta)
        mapped_rows.append(
            {
                "title": ev.title,
                "start_date": ev.start_kst.strftime("%Y-%m-%d %H:%M"),
                "days_left": days_left,
                "priority": default_priority,
                "predicted_hours": predicted_hours,
                "task_slug": task.task_id,
                "matched_by": match.method,
                "match_confidence": round(match.confidence, 3),
            }
        )
        touched_task_ids.append(task.task_id)

        links[match.fingerprint] = {
            "task_id": task.task_id,
            "method": match.method,
            "confidence": round(match.confidence, 3),
            "updated_at": now.isoformat(),
        }

    task_total_hours: dict[str, float] = {}
    for row in mapped_rows:
        task_total_hours[row["task_slug"]] = task_total_hours.get(row["task_slug"], 0.0) + float(row["predicted_hours"])

    for row in mapped_rows:
        total_hours_30d = round(task_total_hours.get(row["task_slug"], 0.0), 2)
        row["total_hours_30d"] = total_hours_30d
        row["score"] = score_event_session(row["priority"], row["days_left"], float(row["predicted_hours"]))
        expected_score = score_event_session(row["priority"], row["days_left"], float(row["predicted_hours"]))
        if abs(float(row["score"]) - float(expected_score)) > 1e-9:
            raise RuntimeError(
                "Guardrail violation: score must be session-based "
                "(score_event_session with predicted_hours)."
            )
        ranked.append(row)

    ranked.sort(key=lambda row: (-row["score"], row["days_left"], row["start_date"]))

    source_path = wiki_dir / "sources" / f"calendar-{today_str}.md"
    query_path = wiki_dir / "queries" / f"schedule-brief-{today_str}.md"
    triage_path = wiki_dir / "queries" / f"schedule-triage-{today_str}.md"
    tasks_index_path = wiki_dir / "summaries" / "tasks-index.md"
    unmapped_path = root / "output" / "calendar" / "unmapped_events.json"

    write_source_snapshot(source_path, in_window, today_str)
    write_daily_brief(
        query_path=query_path,
        items=ranked,
        today_str=today_str,
        daily_log_slug=daily_log_slug,
        routine_slug="personal-routine",
    )
    write_triage_report(triage_path, unmapped, skipped_canceled, today_str)
    write_unmapped_events_json(unmapped_path, unmapped, skipped_canceled, today_str)
    ensure_tasks_index(tasks_index_path, active_task_ids(catalog), today_str)
    save_links(links_path, links)

    all_task_count = len(active_task_ids(catalog))
    update_index(wiki_dir / "index.md", today_str, all_task_count)
    append_log(wiki_dir / "log.md", today_str, len(set(touched_task_ids)), len(unmapped))

    print(f"Built schedule brief for {len(in_window)} events in next {args.window_days} days")
    print(f"- source: {source_path}")
    print(f"- query:  {query_path}")
    print(f"- triage: {triage_path}")
    print(f"- tasks in window: {len(set(touched_task_ids))} docs")
    print(f"- tasks total:     {all_task_count} docs")
    print(f"- unmapped events: {len(unmapped)}")
    print(f"- canceled events: {len(skipped_canceled)}")


if __name__ == "__main__":
    main()
