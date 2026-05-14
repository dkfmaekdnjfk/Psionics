#!/usr/bin/env python3
"""
fsrs_update.py — 복습 후 FSRS 필드를 업데이트하는 스크립트.

사용법 (Claude가 내부적으로 호출):
  python3 fsrs_update.py <파일경로> <grade>

  grade: again | hard | good | easy
         (또는 숫자: 1 | 2 | 3 | 4)

예:
  python3 fsrs_update.py wiki/concepts/entropy.md good
  python3 fsrs_update.py wiki/concepts/kl-divergence.md 3
"""

import re
import sys
import math
import yaml
from pathlib import Path
from datetime import date, timedelta, datetime

# ── 설정 ───────────────────────────────────────────────────────────────────────
WIKI_ROOT   = Path(__file__).parent.parent
TARGET_R    = 0.90

DECAY  = -0.5
FACTOR = 0.9 ** (1 / DECAY) - 1

# grade → 숫자 매핑
GRADE_MAP = {"again": 1, "hard": 2, "good": 3, "easy": 4,
             "1": 1, "2": 2, "3": 3, "4": 4}

# 첫 복습 시 초기 stability (grade별)
INIT_STABILITY = {1: 0.4, 2: 1.2, 3: 2.5, 4: 5.0}

# 난이도 변화량 (grade별)
DIFFICULTY_DELTA = {1: +1.5, 2: +0.5, 3: 0.0, 4: -1.0}

# ── 유틸 ───────────────────────────────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text, None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, text[m.end():], m

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

def retrievability(t_days: float, stability: float) -> float:
    """현재 기억 유지율 R(t, S)."""
    if stability is None or stability <= 0 or t_days < 0:
        return 1.0
    return (1 + FACTOR * t_days / stability) ** DECAY

def next_interval(stability: float, target_r: float = TARGET_R) -> int:
    """안정도(stability)로 다음 복습 간격(일) 계산."""
    interval = stability / FACTOR * ((target_r ** (1 / DECAY)) - 1)
    return max(1, math.ceil(interval))

def update_stability(s_old, r_current: float, grade: int) -> float:
    """
    FSRS-inspired stability 업데이트.
    - again: 초기값으로 리셋
    - hard/good/easy: 현재 R과 grade에 따라 성장
    """
    if grade == 1:  # again
        return INIT_STABILITY[1]

    if s_old is None:
        # 첫 복습
        return INIT_STABILITY[grade]

    # FSRS stability growth formula (단순화)
    # s_new = s_old * (e^(w_r * (grade - 3)) * (11 - difficulty) * r^(-0.5) + 1)
    # 여기서는 직관적인 근사값 사용
    grade_boost = math.exp(0.9 * (grade - 3))   # good=1.0, easy=e^0.9≈2.46, hard=e^-0.9≈0.41
    recall_boost = max(0.1, r_current) ** (-0.3)  # 기억률 낮을수록 더 큰 성장
    new_s = s_old * grade_boost * recall_boost
    return max(new_s, INIT_STABILITY[grade])

def update_difficulty(d_old: float, grade: int) -> float:
    """난이도(difficulty) 업데이트. 1~10 범위로 클리핑."""
    delta = DIFFICULTY_DELTA[grade]
    return max(1.0, min(10.0, d_old + delta))

def replace_fsrs_fields(fm_text: str, updates: dict) -> str:
    """frontmatter 원문에서 FSRS 필드 값만 교체."""
    result = fm_text
    for key, val in updates.items():
        # 기존 값 교체 (null 포함)
        pattern = re.compile(rf"^({key}:\s*).*$", re.MULTILINE)
        if val is None:
            new_val = "null"
        elif isinstance(val, float):
            new_val = f"{val:.4f}"
        else:
            new_val = str(val)
        result = pattern.sub(rf"\g<1>{new_val}", result)
    return result

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("사용법: python3 fsrs_update.py <파일경로> <grade>")
        print("  grade: again | hard | good | easy  (또는 1~4)")
        sys.exit(1)

    file_arg = sys.argv[1]
    grade_arg = sys.argv[2].lower()

    # 경로 해석 (wiki/ 상대경로 또는 절대경로)
    path = Path(file_arg)
    if not path.is_absolute():
        path = WIKI_ROOT / file_arg
    if not path.exists():
        # wiki/ 접두어 없이 concepts/... 형태도 허용
        path = WIKI_ROOT / file_arg
    if not path.exists():
        print(f"❌  파일 없음: {path}")
        sys.exit(1)

    grade = GRADE_MAP.get(grade_arg)
    if grade is None:
        print(f"❌  알 수 없는 grade: {grade_arg}  (again/hard/good/easy 또는 1~4)")
        sys.exit(1)

    today = date.today()
    text = path.read_text(encoding="utf-8")
    fm, body, match = parse_frontmatter(text)

    if not match:
        print(f"❌  frontmatter 없음: {path}")
        sys.exit(1)

    # 현재 값 읽기
    s_old = fm.get("stability")
    d_old = float(fm.get("difficulty") or 5.0)
    last_reviewed = parse_date(fm.get("last_reviewed"))
    review_count  = int(fm.get("review_count") or 0)

    # 현재 기억률 계산
    if s_old and last_reviewed:
        t_days = (today - last_reviewed).days
        r_current = retrievability(t_days, s_old)
    else:
        r_current = 1.0

    # FSRS 업데이트
    s_new = update_stability(s_old, r_current, grade)
    d_new = update_difficulty(d_old, grade)
    interval = next_interval(s_new)
    next_review = today + timedelta(days=interval)

    grade_labels = {1: "Again ❌", 2: "Hard 😓", 3: "Good ✅", 4: "Easy 🌟"}

    updates = {
        "stability":    round(s_new, 4),
        "difficulty":   round(d_new, 2),
        "last_reviewed": today.isoformat(),
        "next_review":  next_review.isoformat(),
        "review_count": review_count + 1,
    }

    # frontmatter 원문만 교체
    fm_raw = match.group(1)
    fm_new = replace_fsrs_fields(fm_raw, updates)
    new_text = text[:match.start()] + f"---\n{fm_new}\n---" + body

    path.write_text(new_text, encoding="utf-8")

    print(f"✅  {path.stem}")
    print(f"   grade        : {grade_labels[grade]}")
    print(f"   stability    : {s_old or 'null'} → {s_new:.2f}일")
    print(f"   difficulty   : {d_old:.1f} → {d_new:.1f}")
    print(f"   다음 복습    : {next_review} (약 {interval}일 후)")
    print(f"   복습 횟수    : {review_count} → {review_count + 1}")

if __name__ == "__main__":
    main()
