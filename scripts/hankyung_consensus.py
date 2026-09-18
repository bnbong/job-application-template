#!/usr/bin/env python3
# --------------------------------------------------------------------------
# 한경컨센서스 리포트 목록 수집기
#
# 한경컨센서스(https://consensus.hankyung.com)는 공식 API 가 없다.
# 검색 결과 목록 페이지의 HTML 을 가져와 표 행을 파싱하는 방식이며,
# 사이트 구조 변경이나 봇 차단으로 언제든 실패할 수 있다.
# 실패하면 조용히 넘어가지 않고 명시적으로 실패를 기록한다.
#
# 여기서 얻는 자료는 "증권사 애널리스트의 전망"이다.
# 사실이 아니라 의견이므로, 산출 문서에서는 반드시 [전망] 태그와
# 작성 증권사·작성일을 함께 남긴다.
#
# @author bnbong
# --------------------------------------------------------------------------
"""한경컨센서스 리포트 목록 수집 CLI.

사용 예:
    python3 scripts/hankyung_consensus.py --corp "네이버" --limit 10
    python3 scripts/hankyung_consensus.py --corp "카카오" --kind industry
    python3 scripts/hankyung_consensus.py --corp "쿠팡" --out job_applications/2026/second_half/coupang/_raw

차단되어 실패하면 종료코드 3 을 반환하고, 사람이 직접 볼 수 있는
검색 URL 을 출력한다. 그 경우 웹 검색이나 브라우저로 대체 조사한다.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any


BASE = "https://consensus.hankyung.com"
LIST_PATH = "/analysis/list"
PDF_PATH = "/analysis/downpdf"

# 리포트 종류 (report_type 파라미터)
KIND_TO_TYPE = {
    "company": "CO",  # 기업 리포트
    "industry": "DO",  # 산업 리포트
    "market": "MO",  # 시황 리포트
    "economy": "EO",  # 경제 리포트
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": BASE + "/",
}


class ConsensusError(RuntimeError):
    """한경컨센서스 접근 실패."""


# --------------------------------------------------------------------------
# 최소 HTTP 클라이언트 (표준 라이브러리만 사용)
#
# 헤드리스 실행 환경의 python3 는 시스템 파이썬일 수 있고 거기에는
# requests 가 없다. 그 한 줄 때문에 수집이 통째로 멈추는 일을 없애려고
# urllib.request 로 필요한 만큼만 다시 만들었다. 직접 처리하는 것은 넷이다.
#   - gzip/deflate 응답 해제
#   - Content-Type 의 charset 추출
#   - 4xx/5xx 를 예외가 아니라 status_code 로 돌려주기 (requests 와 같은 동작)
#   - UA 헤더와 timeout
# --------------------------------------------------------------------------
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_CHARSET_RE = re.compile(r"""charset\s*=\s*["']?([A-Za-z0-9_.\-]+)""", re.I)


class HttpError(RuntimeError):
    """네트워크 계층 실패 (DNS/TLS/타임아웃). HTTP 상태 코드 오류는 여기 해당하지 않는다."""


class HttpResponse:
    """urllib 응답을 requests.Response 처럼 쓰기 위한 최소 래퍼."""

    def __init__(self, url: str, status_code: int, headers: Any, content: bytes) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.content = content
        try:
            ctype = headers.get("Content-Type", "") or ""
        except AttributeError:
            ctype = ""
        m = _CHARSET_RE.search(ctype)
        self.encoding = m.group(1) if m else None

    @property
    def apparent_encoding(self) -> str:
        """본문 바이트로 인코딩을 추정한다. utf-8 -> cp949 순으로만 본다."""
        for enc in ("utf-8", "cp949"):
            try:
                self.content.decode(enc)
                return enc
            except UnicodeDecodeError:
                continue
        return "utf-8"

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding or "utf-8", errors="replace")
        except LookupError:
            # 서버가 알 수 없는 charset 을 적어 보내는 경우
            return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


def _decompress(raw: bytes, headers: Any) -> bytes:
    """Content-Encoding 이 gzip/deflate 면 푼다."""
    try:
        enc = (headers.get("Content-Encoding", "") or "").lower()
    except AttributeError:
        return raw
    if "gzip" in enc:
        try:
            return gzip.decompress(raw)
        except (OSError, EOFError):
            return raw
    if "deflate" in enc:
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                return zlib.decompress(raw, wbits)
            except zlib.error:
                continue
        return raw
    return raw


def http_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> HttpResponse:
    """GET 요청. HTTP 오류 상태도 예외 없이 HttpResponse 로 돌려준다."""
    if params:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urllib.parse.urlencode(params)}"

    merged = {"User-Agent": DEFAULT_UA, "Accept-Encoding": "gzip, deflate"}
    if headers:
        merged.update(headers)

    req = urllib.request.Request(url, headers=merged, method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return HttpResponse(
                url, resp.status, resp.headers, _decompress(resp.read(), resp.headers)
            )
    except urllib.error.HTTPError as exc:
        # 상태 코드로 분기하는 호출부를 위해 예외 대신 응답으로 바꾼다.
        try:
            body = _decompress(exc.read(), exc.headers)
        except Exception:  # noqa: BLE001 - 본문을 못 읽어도 상태 코드는 살린다
            body = b""
        return HttpResponse(url, exc.code, exc.headers, body)
    except urllib.error.URLError as exc:
        raise HttpError(f"{url} 요청 실패: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise HttpError(f"{url} 요청 실패: {exc}") from exc



DEFAULT_DAYS = 365


def resolve_period(days: int, sdate: str, edate: str) -> tuple[str, str]:
    """조회 기간을 정한다.

    sdate/edate 를 비워서 보내면 사이트가 "오늘 하루"로 기본값을 잡아 버려
    결과가 0건이 된다. 그래서 항상 명시적으로 채워 보낸다.
    기본값은 edate=오늘, sdate=오늘-days.
    """
    end = date.fromisoformat(edate) if edate else date.today()
    start = date.fromisoformat(sdate) if sdate else end - timedelta(days=days)
    if days < 0 or start > end:
        raise ValueError("조회 일수는 0 이상이고 시작일은 종료일 이전이어야 합니다.")
    return start.isoformat(), end.isoformat()


def build_search_url(query: str, kind: str, limit: int, sdate: str, edate: str) -> str:
    """사람이 브라우저로 열 수 있는 검색 URL 을 만든다."""
    report_type = KIND_TO_TYPE.get(kind, "CO")
    return (
        f"{BASE}{LIST_PATH}?"
        f"sdate={sdate}&edate={edate}&now_page=1&search_text={urllib.parse.quote(query)}"
        f"&pagenum={max(limit, 20)}&report_type={report_type}"
    )


_TAG_RE = re.compile(r"<[^>]+>")
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_IDX_RE = re.compile(r"report_idx=(\d+)")
_DATE_RE = re.compile(r"\d{4}[-./]\d{2}[-./]\d{2}")


# <meta charset="..."> / <meta http-equiv content="...; charset=..."> 둘 다 본다.
_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.I
)


def _normalize(text: str) -> str:
    """비교용 정규화. 공백과 (주)·주식회사 표기 차이를 지운다."""
    text = re.sub(r"\(\s*주\s*\)|주식회사", "", text)
    return re.sub(r"\s+", "", text).lower()


def matches_query(items: list[dict[str, str]], query: str) -> int:
    """제목에 검색어가 들어간 행이 몇 건인지 센다.

    한경컨센서스는 검색어가 안 맞아도 빈 결과 대신 전체 목록을 돌려주는 일이 있다.
    행 수만 보고 성공으로 판정하면 엉뚱한 회사의 리포트를 그 회사 것으로 적게 된다.
    """
    needle = _normalize(query)
    if not needle:
        return 0
    return sum(
        1 for it in items if needle in _normalize(it.get("title", ""))
    )


def decode_response(resp: HttpResponse) -> str:
    """응답 인코딩을 정한다. 헤더 -> <meta charset> -> 문자 분포 순으로 본다.

    한경컨센서스는 Content-Type 에 charset 을 안 붙이는 일이 잦다. 그때 본문을
    ISO-8859-1 이나 기본 인코딩으로 읽으면 한글이 전부 깨지고 회사명 대조가 통째로 실패한다.
    """
    declared = resp.encoding
    if not declared or declared.lower() in ("iso-8859-1", "latin-1", "latin1"):
        m = _META_CHARSET_RE.search(resp.content[:4096])
        if m:
            resp.encoding = m.group(1).decode("ascii", errors="ignore")
        else:
            resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _clean(cell_html: str) -> str:
    text = _TAG_RE.sub(" ", cell_html)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


_ANCHOR_RE = re.compile(
    r"""<a[^>]+href=["'][^"']*downpdf\?report_idx=\d+[^"']*["'][^>]*>(.*?)</a>""",
    re.S | re.I,
)


def parse_list_html(page_html: str) -> list[dict[str, str]]:
    """검색 결과 표에서 리포트 행을 추출한다.

    실제 목록 표의 td 순서는
        작성일 | 제목 | 적정가격(목표주가) | 투자의견 | 작성자 | 제공출처(증권사) | 기타
    이다. 제목 td 안에는 같은 문구가 링크·툴팁으로 세 번 중첩돼 있으므로
    PDF 링크(<a href=".../downpdf?report_idx=...">)의 anchor 텍스트만 취한다.
    td 가 없는 행(헤더 행 등)은 건너뛴다.
    """
    items: list[dict[str, str]] = []
    for row_html in _ROW_RE.findall(page_html):
        idx_match = _IDX_RE.search(row_html)
        if not idx_match:
            continue
        cells = [_clean(c) for c in _CELL_RE.findall(row_html)]
        if not cells:
            continue

        anchor = _ANCHOR_RE.search(row_html)
        title = _clean(anchor.group(1)) if anchor else ""
        if not title and len(cells) > 1:
            # 링크 파싱이 실패하면 제목 셀의 첫 줄만 취해 중첩 중복을 피한다.
            title = cells[1].split("  ")[0].strip()

        def cell(i: int) -> str:
            return cells[i] if i < len(cells) else ""

        date_text = cell(0) if _DATE_RE.fullmatch(cell(0)) else next(
            (c for c in cells if _DATE_RE.fullmatch(c)), ""
        )

        report_idx = idx_match.group(1)
        items.append(
            {
                "report_idx": report_idx,
                "date": date_text,
                "title": title,
                "target_price": cell(2),
                "opinion": cell(3),
                "analyst": cell(4),
                "broker": cell(5),
                "raw_cells": " | ".join(c for c in cells if c),
                "pdf_url": f"{BASE}{PDF_PATH}?report_idx={report_idx}",
            }
        )
    return items


def fetch_reports(
    query: str,
    kind: str,
    limit: int,
    sdate: str,
    edate: str,
    timeout: int = 20,
) -> dict[str, Any]:
    """검색 결과를 가져온다. 실패 시 ConsensusError."""
    url = build_search_url(query, kind, limit, sdate, edate)
    try:
        resp = http_get(url, headers=HEADERS, timeout=timeout)
    except HttpError as exc:
        raise ConsensusError(f"네트워크 오류: {exc}") from exc

    if resp.status_code != 200:
        raise ConsensusError(f"HTTP {resp.status_code} (봇 차단 가능). URL: {url}")

    body = decode_response(resp)
    if "report_idx" not in body:
        raise ConsensusError(
            "응답에 리포트 링크가 없습니다. 사이트 구조가 바뀌었거나 차단되었을 수 있습니다. "
            f"직접 확인용 URL: {url}"
        )

    items = parse_list_html(body)
    if not items:
        raise ConsensusError(f"표 파싱에 실패했습니다. 직접 확인용 URL: {url}")

    # 행이 나왔다고 검색이 먹은 것은 아니다. 검색어가 들어간 행이 하나도 없으면
    # 다른 회사의 목록을 받아 온 것으로 보고 실패로 처리한다.
    matched_items = [item for item in items if matches_query([item], query)]
    if not matched_items:
        raise ConsensusError(
            f"검색어 불일치 가능: '{query}' 가 들어간 결과 행이 없습니다 "
            f"(행 {len(items)}건은 받았습니다). 검색이 무시되고 전체 목록이 왔거나, "
            f"등록된 표기가 다를 수 있습니다. 직접 확인용 URL: {url}"
        )

    items = matched_items[:limit]
    return {
        "query": query,
        "kind": kind,
        "sdate": sdate,
        "edate": edate,
        "search_url": url,
        "source": "한경컨센서스 (https://consensus.hankyung.com)",
        "count": len(items),
        "matched_count": len(items),
        "page_matched_count": len(matched_items),
        "encoding": resp.encoding,
        "reports": items,
    }


def download_pdf(report_idx: str, out_dir: Path, timeout: int = 60) -> Path:
    """리포트 PDF 를 내려받는다. 실패 시 ConsensusError."""
    url = f"{BASE}{PDF_PATH}?report_idx={report_idx}"
    headers = dict(HEADERS)
    headers["Referer"] = f"{BASE}{LIST_PATH}"
    try:
        resp = http_get(url, headers=headers, timeout=timeout)
    except HttpError as exc:
        raise ConsensusError(f"PDF 다운로드 실패: {exc}") from exc
    if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
        raise ConsensusError(f"PDF 가 아닙니다 (HTTP {resp.status_code}). URL: {url}")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConsensusError(f"PDF 폴더 생성 실패: {exc}") from exc
    target = out_dir / f"hankyung_{report_idx}.pdf"
    try:
        target.write_bytes(resp.content)
    except OSError as exc:
        raise ConsensusError(f"PDF 저장 실패: {exc}") from exc
    return target


def to_markdown(data: dict[str, Any], today: str) -> str:
    lines = [
        f"# 한경컨센서스 원자료 - {data['query']}",
        "",
        f"- 리포트 종류: {data['kind']}",
        f"- 검색어 '{data['query']}' 가 확인된 행: {data.get('matched_count', '-')}/{data['count']}건",
        "",
        "> 아래는 **증권사 애널리스트의 전망·의견**이다. 사실이 아니다.",
        "> 문서에 인용할 때는 `[전망]` 태그와 증권사명·작성일을 반드시 함께 적는다.",
        "",
        "| 작성일 | 제목 | 증권사 | 애널리스트 | 투자의견 | 목표주가 | PDF 링크 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in data["reports"]:
        lines.append(
            f"| {r['date'] or '-'} | {r['title'] or '-'} | {r['broker'] or '-'} "
            f"| {r.get('analyst') or '-'} | {r.get('opinion') or '-'} "
            f"| {r.get('target_price') or '-'} | [{r['report_idx']}]({r['pdf_url']}) |"
        )
    lines.append("")
    for r in data["reports"]:
        if "local_pdf" in r:
            lines.append(f"- PDF {r['report_idx']}: {r['local_pdf']}")
    lines += [
        "",
        f"- 조회 기간: {data['sdate']} ~ {data['edate']}",
        f"- 조회일: {today}",
        f"- 출처: {data['source']}",
        f"- 검색 URL: {data['search_url']}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="한경컨센서스에서 리포트 목록을 수집한다 (비공식 파싱).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--corp", required=True, help="검색어 (회사명 또는 산업 키워드)")
    parser.add_argument(
        "--kind",
        default="company",
        choices=sorted(KIND_TO_TYPE),
        help="리포트 종류 (기본 company)",
    )
    parser.add_argument("--limit", type=int, default=10, help="가져올 리포트 수 (기본 10)")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"조회 기간 일수, edate 기준 역산 (기본 {DEFAULT_DAYS}일)",
    )
    parser.add_argument("--sdate", default="", help="조회 시작일 YYYY-MM-DD (기본 edate-days)")
    parser.add_argument("--edate", default="", help="조회 종료일 YYYY-MM-DD (기본 오늘)")
    parser.add_argument("--out", help="결과 저장 디렉터리 (hankyung_raw.md/.json 생성)")
    parser.add_argument(
        "--download-pdf",
        "--download",
        dest="download_pdf",
        type=int,
        default=0,
        help="상위 N건 PDF 다운로드 (_raw/pdf/ 에 저장)",
    )
    parser.add_argument("--json", action="store_true", help="JSON 만 표준출력")
    parser.add_argument("--today", default="", help="조회일 표기 (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    args.corp = args.corp.strip()
    if not args.corp or args.limit <= 0 or args.days < 0 or args.download_pdf < 0:
        print("[실패] 회사명은 비울 수 없고 limit > 0, days >= 0, download-pdf >= 0이어야 합니다.", file=sys.stderr)
        return 2

    try:
        today = date.fromisoformat(args.today).isoformat() if args.today else date.today().isoformat()
        sdate, edate = resolve_period(args.days, args.sdate, args.edate)
    except (ValueError, OverflowError) as exc:
        print(f"[실패] 날짜 또는 조회 기간 오류 (YYYY-MM-DD): {exc}", file=sys.stderr)
        return 2

    try:
        data = fetch_reports(args.corp, args.kind, args.limit, sdate, edate)
    except ConsensusError as exc:
        print(f"[실패] 한경컨센서스 자동 수집 불가: {exc}", file=sys.stderr)
        print(
            "[대체] 웹 검색이나 브라우저로 '<회사명> 증권사 리포트 전망' 을 조사하거나 "
            "위 URL 을 브라우저로 직접 열어 확인하세요.",
            file=sys.stderr,
        )
        return 3

    data["retrieved_at"] = today
    if args.download_pdf:
        out_dir = Path(args.out or ".") / "pdf"
        for r in data["reports"][: args.download_pdf]:
            try:
                path = download_pdf(r["report_idx"], out_dir)
                r["local_pdf"] = str(path)
            except ConsensusError as exc:
                r["local_pdf"] = f"실패: {exc}"
                print(f"[경고] PDF {r['report_idx']} 다운로드 실패: {exc}", file=sys.stderr)

    md = to_markdown(data, today)
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hankyung_raw.md").write_text(md, encoding="utf-8")
        (out_dir / "hankyung_raw.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not args.json:
            print(f"저장 완료: {out_dir / 'hankyung_raw.md'}")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif not args.out:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
