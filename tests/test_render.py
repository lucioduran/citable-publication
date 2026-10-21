from html.parser import HTMLParser
import json
import unittest

from citable_publication.model import parse_document
from citable_publication.render import digest, render_files, render_html, render_json, render_markdown
from tests.test_model import sample


class TextCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.code = []
        self.cells = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag in ("code", "td", "th"):
            self.current = tag
            self.text = []

    def handle_data(self, data):
        if self.current:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == self.current:
            (self.code if tag == "code" else self.cells).append("".join(self.text))
            self.current = None


class RenderTests(unittest.TestCase):
    def test_html_preserves_literal_code_and_cells(self):
        source = sample()
        source["sections"][0]["blocks"][1]["text"] = '<script>alert("x")</script>\n\tprint("&")\n'
        source["sections"][0]["blocks"][2]["rows"] = [["<b>literal</b>", "a | b & c"]]
        parser = TextCollector()
        parser.feed(render_html(parse_document(source)).decode())
        self.assertEqual(parser.code, [source["sections"][0]["blocks"][1]["text"]])
        self.assertEqual(parser.cells, ["Name", "Value", "<b>literal</b>", "a | b & c"])
        self.assertNotIn("script", parser.tags)
        self.assertNotIn("b", parser.tags)

    def test_markdown_fences_do_not_close_on_source_backticks(self):
        source = sample()
        source["sections"][0]["blocks"][1]["text"] = "```\n````\nend\n"
        result = render_markdown(parse_document(source)).decode()
        self.assertIn("`````python\n```\n````\nend\n\n`````", result)
        self.assertIn('<a id="details"></a>', result)
        self.assertIn("&lt;content&gt; &amp; text", result)

    def test_json_contains_exact_payload_and_citations(self):
        document = parse_document(sample())
        result = json.loads(render_json(document))
        citations = result.pop("citations")
        self.assertEqual(result, sample())
        self.assertEqual(citations, [{"id": "details", "title": "Details", "url": "https://example.com/example#details"}])

    def test_manifest_covers_all_bytes_deterministically(self):
        documents = (parse_document(sample()),)
        files = render_files(documents)
        self.assertEqual(files, render_files(documents))
        manifest = json.loads(files["manifest.json"])
        covered = set()
        for entry in manifest["documents"]:
            for representation in entry["representations"].values():
                path = representation["path"]
                covered.add(path)
                self.assertEqual(digest(files[path]), representation["sha256"])
                self.assertEqual(len(files[path]), representation["bytes"])
        self.assertEqual(covered, set(files) - {"manifest.json"})


if __name__ == "__main__":
    unittest.main()
