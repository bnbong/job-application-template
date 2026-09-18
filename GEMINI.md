# GEMINI.md - Job Application Assistant Guidelines

이 프로젝트는 채용 공고(JD) 분석, 기업 조사, 자기소개서 및 이력서 작성, 글자 수 계산 등 입사 지원 프로세스 전반을 자동화 및 구조화하기 위한 템플릿입니다.

## 프로젝트 구조 (Project Structure)

- `templates/`: 지원서 작성용 표준 템플릿 (`resume.md`, `coverletter.md`, `company_analysis.md`, `facts.md` 등)
- `workflows/`: 지원 단계별 AI 워크플로우 지침 (`apply-to-posting.md`)
- `scripts/`: 지원 과정에 필요한 파이썬 유틸리티 스크립트
  - `count_essay_chars.py`: 자기소개서 글자 수(공백 포함/제외) 정확한 측정
  - `hankyung_consensus.py`: 한경 컨센서스 기업/산업 분석 리포트 데이터 수집
- `examples/fictional/`: 서류 작성 및 기업 분석 예시 데이터
- `tests/`: 스크립트 동작 검증용 Pytest 단위 테스트 코드 (`tests/test_*.py`)

---

## 주요 실행 명령어 (Commands)

- **테스트 실행**: `pytest`
- **글자 수 측정**: `python scripts/count_essay_chars.py <파일경로>`
- **기업 리포트 수집**: `python scripts/hankyung_consensus.py <키워드>`

---

## Gemini AI 수행 지침 (Agent Guidelines)

### 1. 서류 작성 및 작업 워크플로우
- 사용자 작업 요청 시 먼저 `workflows/apply-to-posting.md`의 단계별 가이드라인을 참조하여 작업을 진행합니다.
- 자기소개서 및 이력서 작성 시 `templates/`에 정의된 마크다운 구조와 `templates/facts.md`(사용자 이력 정보)를 기반으로 작성합니다.
- 공백 포함/제외 글자 수 제한 규칙이 있는 경우, 반드시 작성 후 `scripts/count_essay_chars.py` 기준 검증 방식을 고려하여 분량을 조절합니다.

### 2. 기업 분석 및 자료 조사
- 채용 공고(JD) 분석 시 `templates/company_analysis.md` 및 `templates/report.md` 양식에 맞춰 인재상, 직무 요구사항, 기업 핵심 가치를 가공하여 제공합니다.

### 3. 코드 개발 및 유지보수
- Python 스크립트 수정 시 불필요한 의존성 추가를 지양하고 기존 코드 스타일을 유지합니다.
- 로직 수정 후에는 반드시 `pytest`를 활용해 기존 테스트가 정상 통과하는지 확인하고, 필요 시 `tests/` 아래에 새로운 테스트 케이스를 추가합니다.