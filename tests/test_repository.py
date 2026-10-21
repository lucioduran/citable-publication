import subprocess
import unittest
from pathlib import Path


class RepositoryPolicyTests(unittest.TestCase):
    def test_tracked_text_has_no_forbidden_dash(self):
        root = Path(__file__).resolve().parents[1]
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
        for name in filter(None, files):
            with self.subTest(path=name):
                self.assertNotIn(chr(0x2014), (root / name).read_text(encoding="utf-8"))

    def test_readme_follows_series_structure(self):
        root = Path(__file__).resolve().parents[1]
        headings = [
            line[3:]
            for line in (root / "README.md").read_text().splitlines()
            if line.startswith("## ")
        ]
        self.assertEqual(
            headings,
            [
                "Problem",
                "Scope",
                "Quick start",
                "Usage",
                "Architecture",
                "Reproduction",
                "Results",
                "Testing",
                "Limitations",
                "Contributing",
                "License",
            ],
        )


if __name__ == "__main__":
    unittest.main()
