# define

## build_daily_schedule_brief.py

### 주요 상수
- 실행 인자: `--repo-root`, `--events-file`, `--window-days`
- 경로 상수: `catalog.json`, `event_task_links.json`, `unmapped_events.json`, `daily-YYYY-MM-DD.md`, `personal-routine.md`

### 주요 데이터 구조
- `Event`
  - `title`, `start_kst`, `end_kst`, `note_meta` 등 캘린더 이벤트 정규화 객체
- `TaskStats`
  - `predicted_hours`, `median_hours`, `ewma_hours`, `sample_count`, `confidence`
  - `sample_count`는 샘플 "일수"(Records의 고유 `date`) 기준
- `CatalogTask`
  - `task_id`, `title`, `default_priority`, `default_eta_hours`, `aliases`
- `MatchResult`
  - `mapped`, `task_id`, `method`, `confidence`, `suggestions`, `fingerprint`, `reason`

### 주요 함수
- `load_events(events_path)`
  - JSON 이벤트를 읽어 `Event[]`로 변환
- `load_catalog(catalog_path)`, `load_links(links_path)`
  - task registry와 이벤트-업무 매핑 캐시 로드
- `match_event_to_task(...)`
  - `note.task_id` → 캐시 링크 → alias 점수 순서로 task 매칭
- `ensure_task_doc(...)`
  - catalog에 등록된 업무 문서 생성/갱신 및 기록 테이블 누적
- `calc_task_stats(hours)`
  - 중앙값 + EWMA 기반 예측시간 계산
  - 신뢰도용 `sample_count`는 시간 블록 수가 아니라 고유 일수 기준
- `write_source_snapshot(...)`
  - `wiki/sources/calendar-YYYY-MM-DD.md` 생성
- `write_daily_brief(...)`
  - `wiki/queries/schedule-brief-YYYY-MM-DD.md` 생성
  - 회차별 `predicted_hours` 우선 정렬
  - `total_hours_30d` 컬럼 포함 (task별 향후 30일 총시간, 보조)

## calendar_task_registry.py

### 역할
- 캘린더 이벤트 제목을 canonical `task_id`로 정규화하는 매칭 모듈

### 주요 함수
- `normalize_text(text)`: 제목 정규화
- `is_canceled_event(title, note_meta)`: 취소 이벤트 판별
- `match_event_to_task(...)`: task 매칭 결과 반환
- `active_task_ids(catalog)`: 활성 task 목록 반환
- `save_links(links_path, links)`: 매칭 캐시 저장

## calendar_ops_lib.py

### 역할
- `build_daily_schedule_brief.py`가 사용하는 핵심 계산/파싱 모듈
- 이벤트 파싱, task 문서 기록 누적, ETA 계산 담당

### 주요 상수
- `KST`: 일정 해석 시간대 (`Asia/Seoul`)
- `NOTE_PATTERN`: 캘린더 notes의 `key: value` 파서 정규식

### 주요 함수
- `score_event_session(priority, days_left, session_hours)`
  - 회차 기준 점수식: `0.5*priority + 0.35*urgency + 0.15*session_hours`

## calendar_ops_output.py

### 역할
- wiki/출력 파일 렌더링 전담 모듈

### 주요 상수
- `DEFAULT_DAILY_ROUTINE_ROWS`
  - daily 로그 신규 생성 시 자동 삽입되는 루틴 기본 행
- `DAILY_LOG_ALLOWED_TYPES`
  - daily `type` 허용 enum: `focus`, `work`, `admin`, `routine`, `waste`, `break`, `incident`

### 주요 함수
- `write_source_snapshot(...)`
- `write_daily_brief(...)`
- `write_triage_report(...)`
- `write_unmapped_events_json(...)`
- `ensure_daily_log(...)`
- `validate_daily_log_types(...)`
  - daily 테이블의 `type` enum 검증, 비허용 타입 목록 반환
- `validate_daily_log_order(...)`
  - daily 테이블의 시간 순서(행 시작 시각 기준) 검증
- `validate_evening_status(...)`
  - `18:00+` 행이 `퇴근/야근`으로 확정되었는지 및 야간 행과의 모순 여부 검증
- `validate_past_planned(...)`
  - 과거 시간대/과거 일자에 `planned`가 남아있는지 검증(위반 시 build에서 실패)
- `ensure_personal_routine(...)`
- `ensure_tasks_index(...)`
- `update_index(...)`
- `append_log(...)`

## run_daily_calendar_brief.sh

### 순서
1. `./scripts/export_calendar.js`
2. `python3 ./scripts/calendar_ops/build_daily_schedule_brief.py --window-days 30`
