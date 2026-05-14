# wiki/scripts

FSRS 복습 워크플로 스크립트 모음.

## 실행 환경
- 필수: 프로젝트 루트의 가상환경 `.venv`
- 의존성: `PyYAML`

## 최초 1회 설정
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install pyyaml
```

## 실행 규칙 (중요)
- 스크립트는 항상 가상환경 Python으로 실행한다.
- 예시:
```bash
.venv/bin/python wiki/scripts/fsrs_scheduler.py
.venv/bin/python wiki/scripts/fsrs_update.py concepts/AGI.md good
.venv/bin/python wiki/scripts/fsrs_init.py
```

## 스크립트
- `fsrs_init.py`: 위키 페이지 frontmatter에 FSRS 필드 초기 삽입
- `fsrs_scheduler.py`: 오늘 복습 대상 계산 후 `wiki/queries/review_YYYY-MM-DD.md` 생성
- `fsrs_update.py`: 카드 평가(again/hard/good/easy) 후 FSRS 필드 갱신

## 복습 대상 범위

- 현재 스케줄러는 `wiki/concepts`만 복습 대상으로 스캔합니다.
- `entities`/`sources`는 복습 큐에 포함하지 않습니다.

## 신규 카드 선택 방식

- `fsrs_scheduler.py`는 신규 후보(`next_review: null`)를 날짜 기반 시드로 셔플한 뒤 `NEW_PER_DAY`만큼 선택합니다.
- 같은 날짜에는 결과가 재현되고, 날짜가 바뀌면 신규 10개 조합이 바뀝니다.

## 진행 순서 (due/new 혼합)

- 리뷰 파일에 `## 🧭 추천 진행 순서` 섹션을 생성합니다.
- 기본 규칙은 `due 2개 → new 1개` 반복이며, due 편향을 줄이면서도 연체 카드를 우선 처리합니다.
