# 채용공고 1건 초안 생성 템플릿

본인의 사실 자료와 채용공고 원문을 바탕으로, 회사가 요구한 지원 문서만 초안으로 만드는 공개용 작업 틀입니다. 생성 결과는 반드시 본인이 원문과 대조한 뒤 사용하세요.

## 준비물

- Python 3.10 이상
- 파일을 읽고 쓸 수 있고 웹 조사가 가능한 AI 도구
- 채용공고 URL 또는 사용자가 직접 저장한 공고 원문
- 기존 이력서, 프로젝트 기록, 자격증처럼 본인의 사실을 확인할 자료

특정 AI 제품, 모델, 스킬 설치를 하지 않아도 됩니다. 웹 접근이 막힌 공고는 원문을 직접 타이핑 후 저장해 검토할 수 있습니다.

시작 전, 로컬에 이 프로젝트 clone:

```bash
git clone <remote repository URL>
```

## 사용자가 준비할 자료와 AI가 만드는 문서

완성된 이력서/포트폴리오/자기소개서를 미리 작성할 필요는 없습니다. 

아래의 첫 실행 프롬프트로 AI가 빈 양식을 만들어주면 사용자가 내용을 채우거나, 이미 가진 자료를 전달해 정리할 수 있습니다.

| 준비 시점 | 자료 | 담을 내용 |
|---|---|---|
| 처음 시작할 때 | [`inputs/intake.md`용 양식](templates/intake.md) | 학력·경력·프로젝트의 기간, 본인 역할, 성과, 자격과 각 사실의 근거 |
| 처음 시작할 때 | [`docs/preferences.md`용 양식](templates/preferences.md) | 희망 직무·지역·고용 형태·제외 조건 |
| 공고를 처리할 때 | 공고 URL 또는 저장한 원문 | 업무·자격요건·제출 서류와 실제 자기소개서 문항·글자 수 제한 |

기존 이력서·포트폴리오·자기소개서는 있으면 선택적으로 제공하면 되고, 없으면 질문지만 채워도 됩니다. 로그인 뒤에만 보이는 제출 문항과 글자 수 제한은 해당 화면에서 직접 복사해 전달하세요.

AI는 입력 자료를 `docs/facts.md`로 정리하고 본인의 검토와 확인을 거친 뒤, `docs/resume/resume.md`·`docs/portfolio/portfolio.md`·`docs/coverletter/coverletter.md`를 생성합니다. 그다음 공고별 초안을 작성하며, 실제 경험에 없는 새 사실은 만들지 않습니다.

## 처음 한 번만 실행할 프롬프트

아래 내용을 사용하는 AI 도구에 그대로 전달하세요:

```text
이 저장소의 AGENTS.md와 workflows/apply-to-posting.md를 끝까지 읽어라.
이미 입력했거나 사용자가 확인한 파일은 덮어쓰지 말고 빠진 파일만 만들어라.
templates/intake.md를 inputs/intake.md로, templates/facts.md를 docs/facts.md로,
templates/preferences.md를 docs/preferences.md로 복사해 내 입력을 정리하라.
내가 사실을 확인한 뒤에만 templates/resume.md, templates/portfolio.md,
templates/coverletter.md를 바탕으로 docs/resume/resume.md,
docs/portfolio/portfolio.md, docs/coverletter/coverletter.md를 작성하라.
근거가 없으면 창작하지 말고 {{확인 필요: ...}}로 남겨라.
개인정보와 작업 자료는 공개 저장소에 커밋하지 마라.
```

AI 도구가 파일을 직접 만들 수 없다면 `templates/`의 파일을 같은 상대 경로에 수동으로 복사하면 됩니다. 

생성되는 자소서 초안 세트 중 개인 작업 자료인 `docs/`, `inputs/`, `job_applications/`, `private/`는 기본적으로 Git에서 제외됩니다. **초안 세트 푸시 전 _반드시_ Git 추적 상태도 확인**하세요.

## 공고 1건 처리

기초 문서 확인이 끝난 뒤 다음 프롬프트를 사용하세요:

```text
AGENTS.md와 workflows/apply-to-posting.md를 따라 이 공고 1건을 처리하라.
공고 URL 또는 원문: {{입력}}
공고 원문에서 확인한 제출 서류만 작성하고, 문항이나 한도를 확인하지 못하면 해당 문서 작성을 보류하라.
docs/facts.md와 본인이 확인한 정리본만 후보자 사실의 근거로 사용하라.
마지막에 templates/report.md 형식으로 검증 상태, 남은 확인 사항, 자수 실측을 보고하라.
커밋하거나 제출하지 마라.
```

결과는 `job_applications/<연도>/<first_half|second_half>/<회사영문소문자>/` 아래에 생성됩니다.

같은 회사의 공고가 둘 이상이면 `<공고식별자>/`를 한 단계 더 두어 기존 초안과 제출본을 덮어쓰지 않습니다. 

기본 산출물은 `JD.md`, `company_analysis.md`, 회사가 요구한 지원 문서, `report.md`입니다.

가상 예제와 자수 도구는 다음 명령으로 확인할 수 있습니다.

```bash
python3 scripts/count_essay_chars.py examples/fictional/coverletter.md
python3 -B tests/test_count_essay_chars.py
```

## 꼭 지킬 것

- `docs/facts.md → 정리본 3종 → 회사별 산출물` 순서로만 수정합니다.
- 경험, 기간, 역할, 기술, 수치를 만들지 않습니다.
- 제출 완료한 지원 문서는 수정하지 않습니다.
- 회사가 요구하지 않은 서류와 확인되지 않은 문항은 만들지 않습니다.
- `scripts/count_essay_chars.py`의 종료코드만 믿지 말고 문항 수, 최소·최대 한도, 97% 기준을 직접 확인합니다.
- 최종 제출과 공개 범위는 본인이 결정합니다.

참고용 가상 완성본은 `examples/fictional/`에 있습니다.
