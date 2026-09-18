"""세 지침 파일의 공통 규약 구간이 서로 같고 import 줄이 없는지 확인한다."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- 공통 규약 시작 -->"
END = "<!-- 공통 규약 끝 -->"
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
STANDALONE_FILES = ("CLAUDE.md", "GEMINI.md")


def read_lines(name):
    return (ROOT / name).read_text(encoding="utf-8").splitlines()


def common_section(name):
    """마커 사이의 줄 목록을 돌려준다. 마커 줄 자체는 포함하지 않는다."""
    lines = read_lines(name)
    start = lines.index(START)
    end = lines.index(END)
    return lines[start + 1:end]


class InstructionSyncTest(unittest.TestCase):
    def test_markers_appear_once(self):
        for name in INSTRUCTION_FILES:
            with self.subTest(file=name):
                lines = read_lines(name)
                self.assertEqual(lines.count(START), 1, f"{name}의 시작 마커가 1개가 아니다")
                self.assertEqual(lines.count(END), 1, f"{name}의 끝 마커가 1개가 아니다")
                self.assertLess(
                    lines.index(START), lines.index(END),
                    f"{name}에서 시작 마커가 끝 마커보다 뒤에 있다",
                )

    def test_common_section_is_identical(self):
        baseline = common_section("AGENTS.md")
        self.assertTrue(baseline, "AGENTS.md의 공통 규약 구간이 비어 있다")
        for name in INSTRUCTION_FILES[1:]:
            with self.subTest(file=name):
                self.assertEqual(
                    common_section(name), baseline,
                    f"{name}의 공통 규약 구간이 AGENTS.md와 다르다",
                )

    def test_no_import_lines(self):
        for name in STANDALONE_FILES:
            with self.subTest(file=name):
                imports = [line for line in read_lines(name) if line.startswith("@")]
                self.assertEqual(imports, [], f"{name}에 import 줄이 남아 있다: {imports}")


if __name__ == "__main__":
    unittest.main()
