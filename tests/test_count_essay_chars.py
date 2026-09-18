"""가상 문항으로 추출 기준과 CLI 종료코드를 확인한다."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "count_essay_chars.py"
spec = importlib.util.spec_from_file_location("count_essay_chars", SCRIPT)
counter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(counter)


class EssayCounterTest(unittest.TestCase):
    def test_extract_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "가상문항.md"
            path.write_text(
                "## 문항 1. 연습 (최소 3자, 최대 100자)\n"
                "가 나\n다 **라**\n"
                "> 작성 메모\n| 제외 표 |\n- 제외 목록\n"
                "<details>\n제외 메모\n</details>\n"
                "```\n제외 코드\n```\n"
                "## 문항 2. 연습 (50자 이내)\n마 바\n",
                encoding="utf-8",
            )
            sections = counter.extract_sections(path)
            self.assertEqual(len(sections), 2)
            self.assertEqual(sections[0][1:], (100, 3, "가 나다 라"))
            self.assertEqual(len(sections[0][3]), 6)
            self.assertEqual(sections[1][1:], (50, None, "마 바"))

            # 97% 초과와 문항 0개는 종료코드만으로 실패를 잡을 수 없다.
            cases = [
                ("## 문항 1 (최소 3자, 최대 100자)\n" + "가" * 97, 0, "통과"),
                ("## 문항 1 (최소 3자, 최대 100자)\n" + "가" * 98, 0, "주의(>97%)"),
                ("## 문항 1 (최소 3자, 최대 100자)\n" + "가" * 101, 1, "초과"),
                ("## 문항 1 (최소 3자, 최대 100자)\n가나", 1, "미달(<3자)"),
                ("## 안내\n문항이 없는 파일입니다.", 0, "헤딩을 찾지 못했다"),
            ]
            for content, exit_code, message in cases:
                with self.subTest(message=message):
                    path.write_text(content, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(path)],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, exit_code, result.stderr)
                    self.assertIn(message, result.stdout)


if __name__ == "__main__":
    unittest.main()
