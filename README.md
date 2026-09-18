# 채용공고 1건 초안 생성 템플릿

내 경험과 채용공고를 바탕으로 회사가 요구한 지원 문서 초안을 만드는 템플릿입니다.

AI가 알아서 기업 분석, 직무 적합성 분석 및 자기소개서 초안 세트를 만들어줍니다.

## 1. 준비할 자료

- 경험 입력용 [`templates/intake.md`](templates/intake.md): 학력·경력·프로젝트의 기간, 역할, 성과와 근거
- 희망 조건용 [`templates/preferences.md`](templates/preferences.md): 직무·지역·고용 형태·제외 조건
- 실제 채용공고 URL 또는 저장한 원문: 업무, 자격요건, 제출 서류, 자기소개서 문항과 글자 수 한도
- 기존 이력서·포트폴리오·자기소개서: 있으면 선택적으로 제공하고, 없으면 위 양식부터 작성

채용 페이지 로그인 뒤에만 보이는 문항과 한도는 직접 복사해서 알려줘야 합니다. AI가 웹에 접근할 수 없으면 공고 원문도 직접 복붙하세요.

## 2. 시작 방법

### CLI 또는 에이전트 도구

저장소를 내려받습니다.

```bash
git clone https://github.com/bnbong/job-application-template.git
cd job-application-template
```

설치와 로그인을 마친 도구를 이 프로젝트 폴더에서 실행하고 [아래 프롬프트](#3-내-자료-정리)를 전달하세요.

도구마다 처음 읽히게하는 진입 파일이 다릅니다.

| 도구 | 진입 파일 |
| --- | --- |
| Codex, Cursor 등 AGENTS.md를 읽는 도구 | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |

세 파일은 모두 같은 `AGENTS.md`와 `workflows/apply-to-posting.md`를 불러오므로 도구가 따르는 규칙은 동일합니다.

표에 없는 AI도구를 사용한다면 3절 프롬프트의 첫 줄처럼 `AGENTS.md`를 읽으라고 직접 지시하면 됩니다.

### 일반 AI 채팅

GitHub의 **Code → Download ZIP**으로 파일을 받거나 필요한 파일 본문을 복사하세요.

`AGENTS.md`, `workflows/apply-to-posting.md`, `templates/` 안의 Markdown 파일을 각각 첨부하거나 붙여넣습니다. 공고 처리 시 본인이 확인한 facts와 정리본도 함께 전달하세요.

## 3. 내 자료 정리

처음 한 번 다음 프롬프트를 전달하세요.

```text
AGENTS.md와 workflows/apply-to-posting.md를 읽고 따른다.
templates/intake.md를 inputs/intake.md로, templates/preferences.md를 docs/preferences.md로,
templates/facts.md를 docs/facts.md로 만들어라.
자료가 비어 있으면 필요한 사실을 질문하고, 근거 없는 내용은 만들지 마라.
내가 docs/facts.md를 확인하기 전에는 정리본 3종을 작성하지 마라.
이미 입력했거나 확인한 파일은 보존하라.
파일에 접근할 수 없다면 결과를 파일별 Markdown으로 출력하라.
```

`docs/facts.md`의 기간·역할·성과·수치와 `{{확인 필요: ...}}` 항목을 직접 확인하세요.
확인이 끝나면 다음 요청으로 정리본 3종을 만듭니다.

```text
내가 확인한 docs/facts.md만 근거로 templates의 양식에 맞춰 docs/resume/resume.md,
docs/portfolio/portfolio.md, docs/coverletter/coverletter.md를 작성하라.
```

## 4. 공고 1건 처리

정리본을 확인한 뒤 공고와 함께 다음 프롬프트를 전달하세요.

```text
AGENTS.md와 workflows/apply-to-posting.md를 따라 이 공고를 처리하라.
공고 URL 또는 원문: {{입력}}
공식 웹 자료와 한경컨센서스를 조사해 별도 내부 검토용 company_analysis.md를 반드시 작성하라.
공고에서 실제로 요구한 제출용 서류만 작성하고, 확인하지 못한 문항이나 한도는 추정하지 마라.
마지막에 templates/report.md 형식으로 검증 상태와 남은 확인 사항을 기록하라.
커밋하거나 제출하지 마라.
```

결과는 `job_applications/<연도>/<first_half|second_half>/<회사>/` 아래에 생성되며, 기본 결과물은 `JD.md`, `company_analysis.md`, 공고가 요구한 지원 문서, `report.md`입니다.

검증 기준과 전체 순서는 [`workflows/apply-to-posting.md`](workflows/apply-to-posting.md)를 따릅니다.

한경컨센서스 수집은 API 키가 필요하지 않습니다. 아래의 회사명과 저장 경로를 실제 값으로 바꿔 실행하세요.

```bash
python3 scripts/hankyung_consensus.py --corp "<회사명>" --limit 10 --download-pdf 3 --out "job_applications/<연도>/<반기>/<회사>/_raw"
```

위 스크립트는 목록과 PDF를 저장해주고, AI가 실제 자료를 읽어 `templates/company_analysis.md`에 맞춰 분석합니다.

DART API 수집 도구는 API 키가 필요해서 이 템플릿에서 제외했습니다.

## 5. 제출 전 검토

- 작성된 사실, 공고 문항과 한도, 남은 `{{확인 필요: ...}}`를 원문과 대조합니다.
- 자수 검증은 필수입니다. 제공된 스크립트를 쓰려면 Python 3.10 이상이 필요합니다.

```bash
python3 scripts/count_essay_chars.py <만들어진 초안세트 폴더>/coverletter.md
```

제출 전 글자 수 검토는 직접 수행하세요.

Git push 전에는 파일 추적 상태를 직접 확인하세요.

참고용 완성본(가상의 회사 분석 예제): [`examples/fictional/`](examples/fictional/)

### 추가로 하면 좋은 것:

- 자연스러운 한글 윤문 스킬 활용:
  - [`fluent-korean(Claude-Code용 스킬)`](https://github.com/snflkd/fluent-korean)
  - [`im-not-ai(Claude-Code & Codex & Copilot & Gemini CLI용 스킬)`](https://github.com/epoko77-ai/im-not-ai)