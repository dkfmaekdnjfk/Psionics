#!/usr/bin/env python3
"""
fsrs_scheduler.py — 오늘 복습할 항목을 계산하고 review 파일을 생성하는 스크립트.

동작:
  1. review_enabled: true인 모든 페이지 스캔
  2. next_review <= 오늘  → 복습 대상 (due)
  3. next_review: null   → 신규 카드 풀 → 하루 최대 NEW_PER_DAY 개 도입
  4. wiki/queries/review_YYYY-MM-DD.md 생성

사용법:
  python3 fsrs_scheduler.py          # 오늘 날짜로 실행
  python3 fsrs_scheduler.py 2026-04-20  # 특정 날짜
"""

import re
import sys
import math
import random
import hashlib
import yaml
from pathlib import Path
from datetime import date, datetime

# ── 설정 ───────────────────────────────────────────────────────────────────────
WIKI_ROOT   = Path(__file__).parent.parent
TARGET_DIRS = ["concepts"]
QUERIES_DIR = WIKI_ROOT / "queries"

NEW_PER_DAY = 10          # 하루에 새로 도입할 신규 카드 수
TARGET_R    = 0.90        # 목표 기억 유지율 (90%)
SHUFFLE_NEW_BY_DAY = True # 신규 카드 후보를 날짜별로 섞어서 도입
SHUFFLE_SALT = "brain-fsrs-v1"
MIX_DUE_PER_BLOCK = 2     # 혼합 진행 시 블록당 due 개수
MIX_NEW_PER_BLOCK = 1     # 혼합 진행 시 블록당 new 개수

# FSRS 망각 모델 파라미터
DECAY  = -0.5
FACTOR = 0.9 ** (1 / DECAY) - 1   # ≈ 0.25

# ── 유틸 ───────────────────────────────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, ""
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(1)

def retrievability(t_days: float, stability: float) -> float:
    """현재 기억 유지율 R(t, S) — FSRS 망각 곡선."""
    if stability is None or stability <= 0:
        return 0.0
    return (1 + FACTOR * t_days / stability) ** DECAY

def days_until_due(stability: float, target_r: float = TARGET_R) -> int:
    """stability 기준으로 다음 복습까지 남은 일수."""
    if stability is None or stability <= 0:
        return 1
    interval = stability / FACTOR * ((target_r ** (1 / DECAY)) - 1)
    return max(1, math.ceil(interval))

def parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None

def daily_seed(today: date, salt: str = SHUFFLE_SALT) -> int:
    """같은 날짜에는 동일, 날짜가 바뀌면 달라지는 재현 가능한 시드."""
    payload = f"{salt}:{today.isoformat()}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:16], 16)

def build_mixed_order(due_pages: list[dict], new_today: list[dict]) -> list[tuple[str, dict]]:
    """
    복습 편향을 줄이기 위해 due/new를 블록 단위로 교차 배치한다.
    기본: due 2개 + new 1개 반복.
    반환: [("due", page_dict), ("new", page_dict), ...]
    """
    mixed: list[tuple[str, dict]] = []
    i_due = 0
    i_new = 0
    n_due = len(due_pages)
    n_new = len(new_today)

    while i_due < n_due or i_new < n_new:
        for _ in range(MIX_DUE_PER_BLOCK):
            if i_due < n_due:
                mixed.append(("due", due_pages[i_due]))
                i_due += 1
        for _ in range(MIX_NEW_PER_BLOCK):
            if i_new < n_new:
                mixed.append(("new", new_today[i_new]))
                i_new += 1
    return mixed

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    today_str = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    today = date.fromisoformat(today_str)

    due_pages = []    # next_review <= today
    new_pages = []    # next_review: null (미도입 신규)

    for dir_name in TARGET_DIRS:
        dir_path = WIKI_ROOT / dir_name
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)

            if not fm.get("review_enabled", False):
                continue

            next_review = parse_date(fm.get("next_review"))
            stability   = fm.get("stability")
            last_reviewed = parse_date(fm.get("last_reviewed"))

            if next_review is None:
                # 신규 카드 풀
                new_pages.append({
                    "path": md_file,
                    "title": md_file.stem,
                    "type": fm.get("type", "?"),
                    "tags": fm.get("tags", []),
                    "review_count": fm.get("review_count", 0),
                })
            elif next_review <= today:
                # 복습 대상
                t_days = (today - (last_reviewed or next_review)).days
                r = retrievability(t_days, stability) if stability else 0.0
                due_pages.append({
                    "path": md_file,
                    "title": md_file.stem,
                    "type": fm.get("type", "?"),
                    "tags": fm.get("tags", []),
                    "review_count": fm.get("review_count", 0),
                    "stability": stability,
                    "retrievability": round(r, 3),
                    "overdue_days": (today - next_review).days,
                })

    # 복습 대상: overdue 많은 순 (가장 급한 것부터)
    due_pages.sort(key=lambda x: -x["overdue_days"])

    # 신규 카드: 날짜별 재현 가능한 셔플 후 오늘 도입할 분량만
    if SHUFFLE_NEW_BY_DAY and new_pages:
        rng = random.Random(daily_seed(today))
        rng.shuffle(new_pages)

    new_today = new_pages[:NEW_PER_DAY]

    # 추천 혼합 순서(due/new 교차)
    mixed_order = build_mixed_order(due_pages, new_today)

    # ── 리뷰 파일 생성 ────────────────────────────────────────────────────────
    QUERIES_DIR.mkdir(exist_ok=True)
    out_path = QUERIES_DIR / f"review_{today_str}.md"

    lines = [
        "---",
        f"type: query",
        f"date: {today_str}",
        f"tags: [review, fsrs]",
        "---",
        "",
        f"# 📚 복습 세션 — {today_str}",
        "",
        f"> **오늘 due**: {len(due_pages)}개 | **신규 도입**: {len(new_today)}개 / {len(new_pages)}개 대기 중",
        "",
        "복습 방법: Claude에게 '오늘 복습 시작해줘' 라고 하면 됩니다.",
        "각 개념마다 Again / Hard / Good / Easy 로 평가하면 다음 복습 일정이 자동 계산됩니다.",
        "",
    ]

    if due_pages:
        lines += [
            "## 🔁 복습 대상 (due)",
            "",
            "| 개념 | 타입 | 복습 횟수 | 현재 기억률 | 연체일 |",
            "|------|------|-----------|-------------|--------|",
        ]
        for p in due_pages:
            r_pct = f"{p['retrievability']*100:.0f}%" if p['retrievability'] else "—"
            lines.append(
                f"| [[{p['title']}]] | {p['type']} "
                f"| {p['review_count']} | {r_pct} | +{p['overdue_days']}일 |"
            )
        lines.append("")

    if new_today:
        lines += [
            f"## 🌱 신규 도입 (오늘 {len(new_today)}개)",
            "",
            "| 개념 | 타입 | 태그 |",
            "|------|------|------|",
        ]
        for p in new_today:
            tag_str = ", ".join(p["tags"]) if isinstance(p["tags"], list) else str(p["tags"])
            lines.append(f"| [[{p['title']}]] | {p['type']} | {tag_str} |")
        lines.append("")

    if not due_pages and not new_today:
        lines += ["## ✅ 오늘 복습할 항목이 없습니다!", ""]
    else:
        lines += [
            "## 🧭 추천 진행 순서 (due/new 혼합)",
            "",
            f"> 블록 규칙: due {MIX_DUE_PER_BLOCK}개 → new {MIX_NEW_PER_BLOCK}개 반복",
            "",
        ]
        for idx, (kind, p) in enumerate(mixed_order, start=1):
            label = "DUE" if kind == "due" else "NEW"
            lines.append(f"{idx}. [{label}] [[{p['title']}]]")
        lines.append("")

    lines += [
        "---",
        f"*generated by fsrs_scheduler.py on {today_str}*",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅  리뷰 파일 생성: {out_path.relative_to(WIKI_ROOT.parent)}")
    print(f"    due {len(due_pages)}개 + 신규 {len(new_today)}개 = 총 {len(due_pages)+len(new_today)}개")
    print(f"    신규 대기 중: {len(new_pages) - len(new_today)}개")

if __name__ == "__main__":
    main()
