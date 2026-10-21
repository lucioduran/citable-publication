import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from citable_publication.__main__ import main
from tests.test_model import sample


class CliTests(unittest.TestCase):
    def test_reports_and_failure_streams(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "source.json"
            corpus.write_text(json.dumps({"schema_version": 1, "documents": [sample()]}))
            args = ["--corpus", str(corpus), "--output", str(root / "release")]
            for command, expected in (("build", 0), ("verify", 0), ("build", 2)):
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main([command, *args]), expected)
                stream = stdout if expected == 0 else stderr
                self.assertEqual(json.loads(stream.getvalue())["passed"], expected == 0)
                self.assertEqual((stderr if expected == 0 else stdout).getvalue(), "")
            (root / "release" / "example.json").unlink()
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["verify", *args]), 1)
            self.assertFalse(json.loads(stdout.getvalue())["passed"])


if __name__ == "__main__":
    unittest.main()
