#!/usr/bin/env python3
"""
fsrs_init.py — wiki 페이지에 FSRS 복습 필드를 일괄 추가하는 스크립트.

- 기존 frontmatter 내용은 절대 수정하지 않음 (FSRS 필드만 추가)
- 이미 FSRS 필드가 있는 페이지는 건너뜀
- dry_run=True 로 실행하면 변경 없이 결과만 출력

사용법:
  python3 fsrs_init.py          # dry-run (기본값)
  python3 fsrs_init.py --apply  # 실제 적용
"""

import os
import re
import sys
import yaml
from pathlib import Path

# ── 설정 ───────────────────────────────────────────────────────────────────────
WIKI_ROOT = Path(__file__).parent.parent  # wiki/
TARGET_DIRS = ["concepts", "entities", "sources"]

# 복습 제외 조건
EXCLUDE_TAGS_ANY = {"business", "건기식", "market-research"}   # 하나라도 있으면 제외
REQUIRE_IF_KM = {"neuro", "ml", "statistics", "math"}          # korean-medicine 있을 때 이 중 하나가 있어야 포함

# ── 유틸 ───────────────────────────────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str):
    """(dict, body_after_frontmatter) 반환. frontmatter 없으면 ({}, text)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[m.end():]
    return fm, body

def should_review(tags: list) -> bool:
    """태그 목록을 보고 복습 대상 여부를 판단."""
    tag_set = set(tags or [])
    # 제외 태그가 하나라도 있으면 False
    if tag_set & EXCLUDE_TAGS_ANY:
        return False
    # korean-medicine이 있는데 neuro/ml/stats/math 중 하나도 없으면 False
    if "korean-medicine" in tag_set and not (tag_set & REQUIRE_IF_KM):
        return False
    # clinic만 있고 neuro 없으면 제외
    if "clinic" in tag_set and not (tag_set & REQUIRE_IF_KM):
        return False
    return True

def fsrs_block(enabled: bool) -> str:
    """추가할 FSRS 필드 블록을 반환."""
    flag = "true" if enabled else "false"
    return (
        f"review_enabled: {flag}\n"
        f"stability: null\n"
        f"difficulty: 5.0\n"
        f"last_reviewed: null\n"
        f"next_review: null\n"
        f"review_count: 0\n"
    )

def inject_fsrs(path: Path, dry_run: bool) -> str:
    """
    파일에 FSRS 필드를 추가.
    반환값: "skipped" | "enabled" | "disabled"
    """
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # 이미 FSRS 필드가 있으면 건너뜀
    if "review_enabled" in fm:
        return "skipped"

    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    enabled = should_review(tags)
    block = fsrs_block(enabled)

    # frontmatter 끝(---) 직전에 삽입
    new_text = FRONTMATTER_RE.sub(
        lambda m: f"---\n{m.group(1)}\n{block}---",
        text,
        count=1
    )

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")

    return "enabled" if enabled else "disabled"

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("🔍  DRY-RUN 모드 — 실제 파일 변경 없음\n")
    else:
        print("✏️   APPLY 모드 — 파일을 실제로 수정합니다\n")

    counts = {"enabled": 0, "disabled": 0, "skipped": 0}
    enabled_list = []
    disabled_list = []

    for dir_name in TARGET_DIRS:
        dir_path = WIKI_ROOT / dir_name
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            result = inject_fsrs(md_file, dry_run=dry_run)
            counts[result] += 1
            rel = md_file.relative_to(WIKI_ROOT)
            if result == "enabled":
                enabled_list.append(str(rel))
            elif result == "disabled":
                disabled_list.append(str(rel))

    # 결과 출력
    print(f"📊  결과 요약")
    print(f"  ✅ 복습 포함 (review_enabled: true)  : {counts['enabled']}개")
    print(f"  ⛔ 복습 제외 (review_enabled: false)  : {counts['disabled']}개")
    print(f"  ⏭️  이미 처리됨 (skipped)              : {counts['skipped']}개")
    print()

    print("── 복습 포함 페이지 ──────────────────────────")
    for p in enabled_list:
        print(f"  ✅  {p}")

    print()
    print("── 복습 제외 페이지 ──────────────────────────")
    for p in disabled_list:
        print(f"  ⛔  {p}")

    if dry_run:
        print()
        print("👆  실제 적용하려면: python3 fsrs_init.py --apply")

if __name__ == "__main__":
    main()
