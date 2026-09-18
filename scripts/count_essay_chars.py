#!/usr/bin/env python3
"""자기소개서 markdown 파일의 문항별 글자 수를 실측한다.

세는 기준 (지원서 입력창에 실제로 붙여넣을 텍스트만):
  - `## 문항 ...` 헤딩 단위로 구간을 나눈다. `### ...` 는 하위 구간(A안/B안, 취미/존경이유 등).
  - 본문 문단 줄만 이어 붙여 len() 으로 센다. 공백 포함, 줄바꿈 제외.
  - 제외: 헤딩, 인용(`>`), 표(`|`), HTML 주석, `<details>` 블록 전체,
          구분선(`---`), 목록 줄, 코드 블록.
  - `**굵게**`·`` `코드` `` 같은 markdown 표기 문자는 제출 텍스트가 아니므로 빼고 센다.
  - 줄 전체가 `**안 A**` 처럼 굵게 표기만 있는 줄은 하위 구간 라벨로 취급한다.

한도는 헤딩의 `(700자 이내)`·`(1,500자)`·`(최대 700자)` 같은 표기에서 읽는다.
`(최소 300자, 최대 700자)` 처럼 하한이 같이 적혀 있으면 하한도 읽어서,
실측이 하한에 못 미치면 "미달" 상태로 표시하고 종료코드 1을 낸다.
하위 구간에 표기가 없으면 상위 문항의 한도(와 하한)를 물려받는다.

사용법:
    python3 scripts/count_essay_chars.py <md파일> [<md파일> ...]
    python3 scripts/count_essay_chars.py <md파일> --limit-ratio 0.97

종료코드: 한도를 넘긴 구간이 있으면 1, 모두 통과하면 0.
"""

import argparse
import re
import sys
from pathlib import Path

# `(700자 이내)`, `(1,500자)`, `(1000자 이하)` 등에서 한도(상한) 숫자를 뽑는다.
RE_LIMIT_STRICT = re.compile(r"(?:한도\s*)?([0-9][0-9,]*)\s*자\s*(?:이내|이하|제한)|한도\s*([0-9][0-9,]*)\s*자")
RE_LIMIT = re.compile(r"\(\s*([0-9][0-9,]*)\s*자")
# `최대 700자`, `최대 1,000자` 처럼 "최대 N자" 형식으로 상한을 적은 경우.
RE_LIMIT_MAX = re.compile(r"최대\s*([0-9][0-9,]*)\s*자")
# `최소 300자` 처럼 하한을 적은 경우. 하한 미달이면 별도로 경고한다.
RE_LIMIT_MIN = re.compile(r"최소\s*([0-9][0-9,]*)\s*자")
RE_H2 = re.compile(r"^##\s+(.*)$")
RE_H3 = re.compile(r"^###\s+(.*)$")
RE_BOLD_ONLY = re.compile(r"^\*\*(.+?)\*\*\s*$")
RE_MD_MARKS = re.compile(r"(\*\*|__|`|~~)")
# 세는 대상이 되는 `##` 헤딩의 머리말. 회사마다 문항 표기가 달라 몇 가지를 받는다.
SECTION_PREFIXES = ("문항", "사전질문", "제출본", "자기소개서", "질문", "Q", "프로젝트", "활동")

# 제출하지 않는 하위 구간(면접용 확장본 등)은 한도 판정에서 뺀다.
SKIP_SUB_KEYWORDS = ("대안", "면접용", "확장본", "미제출", "제출 안 함")

RE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def parse_limit(heading: str):
    """헤딩 문자열에서 (상한, 하한) 을 읽는다. 표기가 없으면 각각 None."""
    limit = None
    m = RE_LIMIT_STRICT.search(heading)
    if m:
        limit = int((m.group(1) or m.group(2)).replace(",", ""))
    if limit is None:
        m = RE_LIMIT_MAX.search(heading)
        if m:
            limit = int(m.group(1).replace(",", ""))
    if limit is None:
        m = RE_LIMIT.search(heading)
        if m:
            limit = int(m.group(1).replace(",", ""))

    min_limit = None
    m = RE_LIMIT_MIN.search(heading)
    if m:
        min_limit = int(m.group(1).replace(",", ""))

    return limit, min_limit


def clean(line: str) -> str:
    """markdown 표기 문자를 제거해 제출 텍스트에 가깝게 만든다."""
    line = RE_LINK.sub(r"\1", line)
    return RE_MD_MARKS.sub("", line)


def is_skippable(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith(">"):          # 인용 — 작성 메모
        return True
    if s.startswith("|"):          # 표
        return True
    if s.startswith("---") or s.startswith("***"):
        return True
    if s.startswith("<!--"):       # HTML 주석
        return True
    if re.match(r"^([-*+]\s|\d+[.)]\s)", s):   # 목록
        return True
    if s.startswith("<"):          # 그 밖의 HTML 태그 줄
        return True
    return False


def extract_sections(path: Path):
    """(라벨, 한도, 본문) 목록을 돌려준다. `문항` 으로 시작하는 구간만 센다."""
    sections = []
    cur = None          # {"label", "limit", "min_limit", "lines"}
    parent_label = None
    parent_limit = None
    parent_min_limit = None
    in_details = 0
    in_code = False
    counting = False    # 지금 구간이 `문항` 구간인가

    def flush():
        if cur and cur["lines"]:
            sections.append(
                (cur["label"], cur["limit"], cur["min_limit"], "".join(cur["lines"]))
            )

    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()

        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        # <details> 블록은 통째로 제외 (작성 전 정리 메모)
        if "<details" in s:
            in_details += 1
            continue
        if "</details>" in s:
            in_details = max(0, in_details - 1)
            continue
        if in_details:
            continue

        m2 = RE_H2.match(raw)
        if m2:
            flush()
            title = m2.group(1).strip()
            counting = any(title.startswith(k) for k in SECTION_PREFIXES)
            parent_label = title
            parent_limit, parent_min_limit = parse_limit(title)
            cur = (
                {
                    "label": title,
                    "limit": parent_limit,
                    "min_limit": parent_min_limit,
                    "lines": [],
                }
                if counting
                else None
            )
            continue

        m3 = RE_H3.match(raw)
        if m3:
            flush()
            if not counting:
                cur = None
                continue
            title = m3.group(1).strip()
            lim, min_lim = parse_limit(title)
            if any(k in title for k in SKIP_SUB_KEYWORDS):
                lim = None          # 제출 대상이 아니므로 상위 한도를 물려받지 않는다
                min_lim = None
            else:
                if lim is None:
                    lim = parent_limit
                if min_lim is None:
                    min_lim = parent_min_limit
            cur = {
                "label": f"{parent_label} / {title}" if parent_label else title,
                "limit": lim,
                "min_limit": min_lim,
                "lines": [],
            }
            continue

        if not counting or cur is None:
            continue

        mb = RE_BOLD_ONLY.match(s)
        if mb:
            # 줄 전체가 굵게 표기뿐이면 하위 라벨로 본다
            base = cur["label"].split(" / ")[0] if " / " in cur["label"] else cur["label"]
            sub = cur["label"] if not cur["lines"] else base
            flush()
            cur = {
                "label": f"{sub} / {mb.group(1).strip()}",
                "limit": cur["limit"],
                "min_limit": cur["min_limit"],
                "lines": [],
            }
            continue

        if is_skippable(raw):
            continue

        cur["lines"].append(clean(s))

    flush()
    return sections


def report(path: Path, ratio: float) -> bool:
    sections = extract_sections(path)
    print(f"\n# {path}")
    if not sections:
        print("  `## 문항 ...` 헤딩을 찾지 못했다.")
        return True

    rows = []
    for label, limit, min_limit, body in sections:
        n = len(body)
        if limit:
            pct = n / limit * 100
            head = f"{pct:5.1f}%"
            if n > limit:
                state = "초과"
            elif min_limit and n < min_limit:
                state = f"미달(<{min_limit:,}자)"
            elif pct > ratio * 100:
                state = f"주의(>{ratio:.0%})"
            else:
                state = "통과"
        else:
            head, state = "    —", "한도 표기 없음"
        rows.append((label, limit, n, head, state))

    cap = 56

    def shorten(label: str) -> str:
        # 길면 앞을 줄이고 뒤(하위 구간 이름)를 남긴다 — A안/B안 구분이 보이게
        return label if len(label) <= cap else "…" + label[-(cap - 1):]

    rows = [(shorten(r[0]),) + r[1:] for r in rows]
    w = min(max(len(r[0]) for r in rows), cap)
    print(f"  {'구간'.ljust(w)}  {'한도':>6}  {'실측':>6}  {'사용률':>7}  상태")
    print(f"  {'-' * w}  {'-' * 6}  {'-' * 6}  {'-' * 7}  {'-' * 8}")
    ok = True
    for label, limit, n, head, state in rows:
        lim_s = f"{limit:,}" if limit else "—"
        print(f"  {label.ljust(w)}  {lim_s:>6}  {n:>6,}  {head:>7}  {state}")
        if state == "초과" or state.startswith("미달"):
            ok = False
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="자기소개서 문항별 글자 수 실측")
    ap.add_argument("files", nargs="+", help="자기소개서 markdown 파일")
    ap.add_argument(
        "--limit-ratio",
        type=float,
        default=0.97,
        help="이 비율을 넘으면 '주의'로 표시한다 (기본 0.97)",
    )
    args = ap.parse_args()

    ok = True
    for f in args.files:
        p = Path(f)
        if not p.is_file():
            print(f"파일을 찾을 수 없다: {f}", file=sys.stderr)
            ok = False
            continue
        if not report(p, args.limit_ratio):
            ok = False
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
