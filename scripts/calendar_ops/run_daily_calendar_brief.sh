#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GUARDRAILS_PATH="$REPO_ROOT/wiki/overview/calendar-ops-guardrails.md"
GUARDRAILS_VERSION="calendar_ops_guardrails_version: 2026-04-23-v3"

cd "$REPO_ROOT"

if [[ ! -f "$GUARDRAILS_PATH" ]]; then
  echo "ERROR: guardrails file is missing: $GUARDRAILS_PATH" >&2
  exit 1
fi

if ! grep -Fq "$GUARDRAILS_VERSION" "$GUARDRAILS_PATH"; then
  echo "ERROR: guardrails version mismatch. expected '$GUARDRAILS_VERSION'" >&2
  exit 1
fi

./scripts/export_calendar.js
python3 ./scripts/calendar_ops/build_daily_schedule_brief.py --repo-root "$REPO_ROOT" --events-file output/calendar/events.json --window-days 30
