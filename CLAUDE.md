# Claude Code 작업 지침

이 저장소는 채용공고 1건에 맞춘 지원 문서 초안을 만드는 Markdown 템플릿입니다. 작업 규칙의 단일 기준은 `AGENTS.md`와 `workflows/apply-to-posting.md` 두 파일이며, 이 파일에는 Claude Code에만 해당하는 내용만 둡니다. 공통 규칙을 바꿀 때는 이 파일이 아니라 `AGENTS.md`를 고칩니다.

@./AGENTS.md
@./workflows/apply-to-posting.md

위 import가 동작하지 않는 환경이라면 `AGENTS.md`와 `workflows/apply-to-posting.md`를 직접 끝까지 읽은 다음에 작업을 시작합니다.

## 저장소 구조

- `templates/`에는 지원 문서와 내부 검토 문서의 양식이 들어 있습니다.
- `examples/fictional/`에는 가상의 회사를 대상으로 작성한 예제가 들어 있고, 이 예제의 값은 형식 참고용이므로 실제 문서에 복사하지 않습니다.
- `scripts/count_essay_chars.py`는 자기소개서의 자수를 실측하고, `scripts/hankyung_consensus.py`는 한경컨센서스의 리포트 목록과 PDF를 수집합니다. 두 스크립트는 외부 패키지 없이 표준 라이브러리만 사용하며 Python 3.10 이상을 요구합니다.
- `tests/`에는 두 스크립트의 단위 테스트가 들어 있습니다.
- `inputs/`, `docs/`, `job_applications/`, `private/`는 사용자의 개인 작업 경로이고 Git 추적에서 제외되어 있습니다.

## 명령

```bash
python3 -m unittest discover -s tests
python3 scripts/count_essay_chars.py <만들어진 초안세트 폴더>/coverletter.md
python3 scripts/hankyung_consensus.py --corp "회사명" --limit 10 --download-pdf 3 --out "job_applications/<연도>/<반기>/<회사>/_raw"
```

## 두 가지 작업 모드

템플릿 사용자로서 공고를 처리하는 작업이라면 `AGENTS.md`와 `workflows/apply-to-posting.md`의 절차를 그대로 따릅니다.

템플릿 자체를 유지보수하는 작업이라면 다음 사항을 지킵니다.

- 특정 제품이나 모델, 에이전트 이름에 의존하는 규칙은 공통 문서에 넣지 않습니다.
- 스크립트는 외부 패키지를 도입하지 않고 표준 라이브러리만 사용합니다.
- 스크립트의 동작을 바꾸면 `tests/`의 테스트와 흐름 문서의 해당 설명을 같은 변경에서 함께 고칩니다.
- 실제 개인 정보나 실제 지원 자료를 Git이 추적하는 파일에 넣지 않습니다.

## Claude Code 참고

- 서브에이전트나 스킬을 사용하더라도 `docs/facts.md`를 사실의 단일 기준으로 삼는 규칙과 윤문 전후를 대조하는 규칙처럼 `AGENTS.md`가 정한 사항이 우선합니다.
- README에 적힌 `humanize-korean`, `im-not-ai` 같은 한글 윤문 스킬은 선택 사항이며, 흐름 문서 5절이 요구하는 윤문 전후 대조 절차를 대체하지 않습니다.
- 사용자가 요청하지 않으면 커밋, 푸시, 제출을 수행하지 않습니다.
