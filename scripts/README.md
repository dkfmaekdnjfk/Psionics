# scripts

캘린더 연동 보조 스크립트 모음.

## export_calendar.js
- 목적: macOS Calendar 앱의 향후 30일 일정을 읽기 전용으로 추출
- 출력: `output/calendar/events.json`
- 실행:
  ```bash
  ./scripts/export_calendar.js
  ```
- 주의:
  - 최초 실행 시 macOS 캘린더 접근 권한 허용 필요
  - 이 스크립트는 일정 생성/수정/삭제를 하지 않음

## calendar_ops/
- 목적: 캘린더 이벤트를 기반으로 업무 문서/ETA/일일 브리핑을 wiki에 반영
- 상세 문서:
  - `scripts/calendar_ops/README.md`
  - `scripts/calendar_ops/define.md`
