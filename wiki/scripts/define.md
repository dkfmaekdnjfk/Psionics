# define.md — wiki/scripts

FSRS 스크립트의 핵심 함수/변수 정의.

## 공통
- `WIKI_ROOT`: `wiki/` 루트 경로 기준값
- `review_enabled`: 복습 대상 여부 플래그
- `stability`: 기억 안정도(일 단위)
- `difficulty`: 난이도(1~10)
- `last_reviewed`: 마지막 복습일
- `next_review`: 다음 복습 예정일
- `review_count`: 누적 복습 횟수

## fsrs_init.py
- `should_review(tags)`: 태그 기반 복습 포함/제외 결정
- `FSRS 블록 삽입 로직`: frontmatter에 초기값(`stability: null`, `difficulty: 5.0` 등) 추가

## fsrs_scheduler.py
- `TARGET_DIRS`: 복습 대상으로 스캔할 디렉토리 목록 (현재 `["concepts"]`)
- `NEW_PER_DAY`: 일일 신규 도입 카드 수
- `SHUFFLE_NEW_BY_DAY`: 신규 후보를 날짜별로 셔플할지 여부
- `SHUFFLE_SALT`: 날짜 셔플 시드 생성용 고정 솔트
- `daily_seed(today, salt)`: 날짜 기반 재현 가능한 시드 생성
- `MIX_DUE_PER_BLOCK`, `MIX_NEW_PER_BLOCK`: due/new 혼합 진행 비율
- `build_mixed_order(due_pages, new_today)`: due/new 교차 추천 순서 생성
- `parse_date(val)`: 날짜 파싱 유틸
- `retrievability(t_days, stability)`: 현재 기억률 계산
- `due_pages`: `next_review <= today`인 복습 대상
- `new_pages`: `next_review == null`인 신규 후보
- `new_today`: 오늘 실제 도입하는 신규 카드 집합

## fsrs_update.py
- `GRADE_MAP`: `again/hard/good/easy` ↔ `1/2/3/4` 매핑
- `INIT_STABILITY`: 첫 복습 등급별 초기 안정도
- `DIFFICULTY_DELTA`: 등급별 난이도 변화량
- `retrievability(t_days, stability)`: 현재 기억률 함수
- `update_stability(s_old, r_current, grade)`: 안정도 업데이트
- `update_difficulty(d_old, grade)`: 난이도 업데이트
- `next_interval(stability, target_r)`: 다음 복습 간격(일) 계산
- `replace_fsrs_fields(fm_text, updates)`: frontmatter FSRS 필드 치환

## 실행 원칙
- 모든 스크립트는 `.venv/bin/python`으로 실행한다.
