# calendar_ops

캘린더 기반 업무 우선순위/예상시간(ETA) 자동 브리핑 모듈.
현재 브리핑 점수는 `회차(이벤트 1건)`를 우선 반영하고, `총시간(30일)`은 보조로 제공합니다.

## 구성
- `calendar_task_registry.py`
  - `wiki/entities/tasks/catalog.json`을 읽어 canonical task registry를 로드
  - `output/calendar/event_task_links.json` 캐시를 이용해 이벤트 제목 매핑 재사용
  - 매핑 실패 이벤트를 triage 대상으로 분류
- `calendar_ops_lib.py`
  - 이벤트 파싱, task 문서 갱신, ETA 계산 공통 함수
- `calendar_ops_output.py`
  - schedule brief/triage/source/index/tasks-index/log 출력 담당
- `build_daily_schedule_brief.py`
  - `output/calendar/events.json`을 읽어 향후 30일 업무를 정렬
  - 회차별 `predicted_hours`로 우선순위 점수화
  - task별 `total_hours_30d`(향후 30일 예상시간 합계)는 보조 컬럼으로 제공
  - catalog에 등록된 task만 문서 갱신 (미등록 task 자동 생성 금지)
  - `wiki/sources/calendar-YYYY-MM-DD.md` 스냅샷 생성
  - `wiki/queries/schedule-brief-YYYY-MM-DD.md` 브리핑 생성
  - `wiki/queries/schedule-triage-YYYY-MM-DD.md` 미매핑/취소 큐 생성
  - `wiki/logs/daily-YYYY-MM-DD.md` 일일 시간기록 파일 생성(없을 때, 기본 루틴 행 자동 삽입)
  - `wiki/overview/personal-routine.md` 고정 루틴 파일 생성(없을 때)
  - `output/calendar/unmapped_events.json` 생성
  - `wiki/summaries/tasks-index.md`, `wiki/index.md`, `wiki/log.md` 갱신
- `run_daily_calendar_brief.sh`
  - `export_calendar.js` + `build_daily_schedule_brief.py` 순서 실행 래퍼

## 캘린더 notes 메타데이터 규칙
아래 키를 이벤트 메모에 `key: value` 형식으로 입력.

- `task_id`: canonical task ID (있으면 최우선)
- `priority`: 1~5 (기본 3)
- `eta_hours`: 예상 소요시간(시간)
- `repeat_key`: 반복 업무 식별 키 (없으면 제목 기반)
- `actual_hours`: 실제 소요시간(완료 후 기록)
- `status`: `canceled`면 브리핑에서 제외

## ETA 샘플 기준
- task 문서의 `sample_count`는 시간 블록 개수가 아니라 `Records`의 고유 `date` 일수 기준입니다.
- `predicted_hours`는 이벤트 회차(1건) 기준으로 계산되며, `sample_count`는 신뢰도 보조지표로 사용됩니다.

## Daily Type Enum
- 허용 `type`: `focus`, `work`, `admin`, `routine`, `waste`, `break`, `incident`
- `build_daily_schedule_brief.py` 실행 시 허용 목록 밖의 `type`은 경고 출력
- `daily` 시간 행이 역순이면(예: 23:00 뒤 18:00) 경고 출력
- `18:00+` 행은 `퇴근` 또는 `야근`으로 확정 기록해야 하며, 미확정/모순 시 경고 출력
- 과거 시간대에 `planned`가 남아 있으면 `build_daily_schedule_brief.py`가 실패(hard-fail)

예시:
```text
task_id: com-neuro-스터디
priority: 4
eta_hours: 2.5
repeat_key: com-neuro-스터디
actual_hours: 2.2
```

## 실행
```bash
./scripts/calendar_ops/run_daily_calendar_brief.sh
```

## 단일 진실(SoT)
- canonical task registry: `wiki/entities/tasks/catalog.json`
- event-task 링크 캐시: `output/calendar/event_task_links.json`
- 미매핑 큐: `wiki/queries/schedule-triage-YYYY-MM-DD.md`
- 일일 로그: `wiki/logs/daily-YYYY-MM-DD.md`
- 고정 루틴: `wiki/overview/personal-routine.md`
