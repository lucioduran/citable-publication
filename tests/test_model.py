import copy
import json
import tempfile
import unittest
from pathlib import Path

from citable_publication.model import PublicationError, load_corpus, parse_document


def sample():
    return {
        "schema_version": 1,
        "slug": "example",
        "canonical": "https://example.com/example",
        "title": "Example",
        "language": "en",
        "sections": [
            {
                "id": "details",
                "title": "Details",
                "blocks": [
                    {"type": "paragraph", "text": "Literal <content> & text."},
                    {"type": "code", "language": "python", "text": "print('hello')\n"},
                    {"type": "table", "headers": ["Name", "Value"], "rows": [["A", "1"]]},
                ],
            }
        ],
    }


class ModelTests(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(parse_document(sample()).to_dict(), sample())

    def test_invalid_document_fields(self):
        for field, values in {
            "schema_version": [True, 2, "1"],
            "language": ["es", None],
            "slug": ["../escape", "UPPER", "", "a/b"],
            "canonical": [
                "http://example.com",
                "https://x/a#b",
                "https://u:p@x/a",
                "https://x:bad",
                "https://x/a b",
            ],
            "title": ["", "x\ny", "x\x00", "x\ud800", "x" + chr(0x2014)],
            "sections": [[], {}, None],
        }.items():
            for value in values:
                with self.subTest(field=field, value=repr(value)):
                    document = sample()
                    document[field] = value
                    with self.assertRaises(PublicationError):
                        parse_document(document)

    def test_unknown_and_missing_fields(self):
        for mutate in (lambda d: d.update(extra=True), lambda d: d.pop("title")):
            document = sample()
            mutate(document)
            with self.assertRaises(PublicationError):
                parse_document(document)

    def test_duplicate_section(self):
        document = sample()
        document["sections"] *= 2
        with self.assertRaisesRegex(PublicationError, "duplicate id"):
            parse_document(document)

    def test_reserved_output_names(self):
        for slug in ("manifest", "con", "aux", "nul", "prn", "com1", "com9", "lpt1", "lpt9"):
            with self.subTest(slug=slug):
                document = sample()
                document["slug"] = slug
                with self.assertRaisesRegex(PublicationError, "reserved"):
                    parse_document(document)

    def test_invalid_blocks(self):
        for block in (
            None,
            {"type": "unknown"},
            {"type": "paragraph"},
            {"type": "table", "headers": [], "rows": []},
            {"type": "table", "headers": ["A"], "rows": [["1", "2"]]},
        ):
            document = sample()
            document["sections"][0]["blocks"] = [block]
            with self.subTest(block=block), self.assertRaises(PublicationError):
                parse_document(document)

    def test_corpus_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            payload = {"schema_version": 1, "documents": [sample()]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(len(load_corpus(path)), 1)
            for content in ('{"schema_version":1,"schema_version":1}', "{}", "[]", "{"):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(PublicationError):
                    load_corpus(path)
            for field in ("slug", "canonical"):
                second = copy.deepcopy(sample())
                second["slug"] = "second"
                second["canonical"] = "https://example.com/second"
                second[field] = sample()[field]
                payload["documents"] = [sample(), second]
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(PublicationError):
                    load_corpus(path)


if __name__ == "__main__":
    unittest.main()
