import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from citable_publication.model import PublicationError, parse_document
from citable_publication.publish import build, verify
from tests.test_model import sample


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "release"
        self.documents = (parse_document(sample()),)

    def test_build_and_verify(self):
        self.assertTrue(build(self.documents, self.output)["passed"])
        self.assertTrue(verify(self.documents, self.output)["passed"])

    def test_each_representation_and_manifest_are_checked(self):
        build(self.documents, self.output)
        for name in ("example.html", "example.md", "example.json", "manifest.json"):
            path = self.output / name
            original = path.read_bytes()
            path.write_bytes(original + b"drift")
            with self.subTest(name=name):
                report = verify(self.documents, self.output)
                self.assertFalse(report["passed"])
                self.assertEqual([item["path"] for item in report["files"] if item["status"] == "mismatch"], [name])
            path.write_bytes(original)

    def test_missing_extra_and_symlink_files_fail(self):
        build(self.documents, self.output)
        (self.output / "example.md").unlink()
        (self.output / "extra.txt").write_text("unexpected")
        (self.output / "example.html").unlink()
        (self.output / "example.html").symlink_to(self.root / "outside")
        statuses = {item["path"]: item["status"] for item in verify(self.documents, self.output)["files"]}
        self.assertEqual(statuses["example.md"], "missing")
        self.assertEqual(statuses["extra.txt"], "unexpected")
        self.assertEqual(statuses["example.html"], "unsafe")

    def test_existing_destination_is_preserved(self):
        build(self.documents, self.output)
        before = (self.output / "example.html").read_bytes()
        with self.assertRaises(PublicationError):
            build(self.documents, self.output)
        self.assertEqual((self.output / "example.html").read_bytes(), before)

    def test_failed_gate_does_not_publish(self):
        with patch("citable_publication.publish.verify", return_value={"passed": False}):
            with self.assertRaises(PublicationError):
                build(self.documents, self.output)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_write_failure_cleans_staging(self):
        with patch("pathlib.Path.write_bytes", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                build(self.documents, self.output)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_and_symlink_directories_fail(self):
        with self.assertRaises(PublicationError):
            verify(self.documents, self.output)
        self.output.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(PublicationError):
            verify(self.documents, self.output)

    def test_cli_exit_codes(self):
        corpus = self.root / "corpus.json"
        corpus.write_text(json.dumps({"schema_version": 1, "documents": [sample()]}))
        def run(command):
            return subprocess.run([sys.executable, "-m", "citable_publication", command,
                                   "--corpus", str(corpus), "--output", str(self.output)],
                                  capture_output=True, text=True, check=False)
        built = run("build")
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertTrue(json.loads(built.stdout)["passed"])
        self.assertEqual(run("verify").returncode, 0)
        (self.output / "example.md").unlink()
        self.assertEqual(run("verify").returncode, 1)
        self.assertEqual(run("build").returncode, 2)
        corpus.write_text("invalid")
        self.assertEqual(run("verify").returncode, 2)


if __name__ == "__main__":
    unittest.main()
