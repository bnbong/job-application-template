"""네트워크 없이 한경컨센서스 수집 경계를 검증한다."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "consensus", Path(__file__).resolve().parents[1] / "scripts/hankyung_consensus.py"
)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def row(idx, title):
    return (f'<tr><td>2026.09.01</td><td><a href="/analysis/downpdf?report_idx={idx}">'
            f'<span>{title}</span></a><div>{title}</div></td><td>10,000</td>'
            '<td>매수</td><td>홍길동</td><td>가상증권</td></tr>')


def response(body, status=200, encoding="utf-8"):
    return h.HttpResponse("https://consensus.hankyung.com", status, {}, body.encode(encoding))


class ConsensusCheck(unittest.TestCase):
    def test_period_and_mixed_company_page(self):
        self.assertEqual(h.resolve_period(365, "", "2026-09-18"), ("2025-09-18", "2026-09-18"))
        for encoding in ("utf-8", "cp949"):
            with self.subTest(encoding=encoding), patch.object(h, "http_get", return_value=response(
                row(1, "다른기업 전망") + row(2, "주식회사 가상기업 성장 &amp; 전망")
                + row(3, "가상기업 성장"), encoding=encoding
            )):
                data = h.fetch_reports("가상기업", "company", 1, "2025-09-18", "2026-09-18")
                self.assertEqual(data["count"], 1)
                self.assertEqual(data["matched_count"], 1)
                self.assertEqual(data["page_matched_count"], 2)
                self.assertEqual(data["reports"][0]["report_idx"], "2")
                self.assertEqual(data["reports"][0]["title"], "주식회사 가상기업 성장 & 전망")
                self.assertEqual(data["reports"][0]["broker"], "가상증권")
                self.assertEqual(data["reports"][0]["date"], "2026.09.01")

    def test_failed_or_unverified_pages(self):
        for resp in (response("차단", 403), response("접근 제한"), response("<table></table>"),
                     response(row(1, "다른기업 성장")), response("report_idx=1")):
            with self.subTest(body=resp.text), patch.object(h, "http_get", return_value=resp):
                with self.assertRaises(h.ConsensusError):
                    h.fetch_reports("가상기업", "company", 10, "2025-09-18", "2026-09-18")
        with patch.object(h, "http_get", return_value=response(row(1, "LG화학 전망").replace("가상증권", "삼성증권"))):
            with self.assertRaises(h.ConsensusError):
                h.fetch_reports("삼성증권", "company", 10, "2025-09-18", "2026-09-18")
        with patch.object(h, "http_get", side_effect=h.HttpError("네트워크 오류")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(h.main(["--corp", "가상기업"]), 3)

    def test_files_json_and_pdf_partial_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(h, "http_get", side_effect=[
            response(row(1, "가상기업 성장") + row(2, "가상기업 전망")),
            h.HttpResponse("pdf", 200, {}, b"%PDF-1.4 test"), response("차단", 403),
        ]), contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = h.main(["--corp", "가상기업", "--out", folder, "--download-pdf", "2", "--json", "--today", "2026-09-18"])
            self.assertEqual(code, 0)
            data = json.loads((Path(folder) / "hankyung_raw.json").read_text())
            self.assertEqual(json.loads(stdout.getvalue()), data)
            self.assertEqual(data["retrieved_at"], "2026-09-18")
            self.assertTrue(Path(data["reports"][0]["local_pdf"]).read_bytes().startswith(b"%PDF"))
            self.assertIn("실패", data["reports"][1]["local_pdf"])
            self.assertIn("[경고]", stderr.getvalue())
            md = (Path(folder) / "hankyung_raw.md").read_text()
            self.assertIn("조회일: 2026-09-18", md)
            self.assertIn("PDF 2: 실패", md)

    def test_invalid_arguments_do_not_fetch(self):
        cases = [["--corp", "  "], ["--limit", "0"], ["--days", "-1"],
                 ["--download-pdf", "-1"], ["--today", "잘못된날짜"],
                 ["--sdate", "2026-10-01", "--edate", "2026-09-01"],
                 ["--edate", "2026-02-30"]]
        for args in cases:
            with self.subTest(args=args), patch.object(h, "http_get") as fetch, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(h.main(["--corp", "가상기업"] + args), 2)
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
