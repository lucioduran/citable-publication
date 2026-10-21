"""Compare canonical-only validation with deterministic publication checks."""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import subprocess
import tempfile

from citable_publication.model import load_corpus
from citable_publication.publish import build, verify
from citable_publication.render import digest, json_bytes


class CanonicalParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.urls.append(attrs.get("href"))


def baseline(documents, directory: Path) -> bool:
    for document in documents:
        parser = CanonicalParser()
        try:
            parser.feed((directory / f"{document.slug}.html").read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            return False
        if parser.urls != [document.canonical]:
            return False
    return True


def inject(directory: Path, document, fault: str) -> None:
    extension = {"canonical": "html", "schema": "json", "code": "md", "table": "html",
                 "missing": "json", "manifest": "json"}[fault]
    path = directory / ("manifest.json" if fault == "manifest" else f"{document.slug}.{extension}")
    if fault == "missing":
        path.unlink()
        return
    content = path.read_text(encoding="utf-8")
    if fault == "canonical":
        content = content.replace(document.canonical, "https://example.org/wrong", 1)
    elif fault == "schema":
        value = json.loads(content)
        value["schema_version"] = 999
        content = json.dumps(value)
    elif fault == "code":
        content = content.replace("return f", "return broken_f", 1)
    elif fault == "table":
        content = content.replace("Versioned source + citations", "Truncated", 1)
    else:
        value = json.loads(content)
        value["documents"] = []
        content = json.dumps(value)
    path.write_text(content, encoding="utf-8")


def reproduce(corpus: Path) -> dict:
    documents = load_corpus(corpus)
    cases = []
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / "release"
        build(documents, directory)
        pristine = {path.name: path.read_bytes() for path in directory.iterdir()}
        cases.append({"case": "clean", "expected_pass": True,
                      "baseline_pass": baseline(documents, directory), "gate_pass": verify(documents, directory)["passed"]})
        for document in documents:
            for fault in ("canonical", "schema", "code", "table", "missing", "manifest"):
                for name, content in pristine.items():
                    (directory / name).write_bytes(content)
                inject(directory, document, fault)
                changed = [name for name, content in pristine.items()
                           if not (directory / name).exists() or (directory / name).read_bytes() != content]
                if not changed:
                    raise RuntimeError(f"Fault injection did not change any bytes: {fault}")
                report = verify(documents, directory)
                cases.append({"case": f"{document.slug}/{fault}", "expected_pass": False,
                              "changed_files": changed, "baseline_pass": baseline(documents, directory),
                              "gate_pass": report["passed"], "report": report})
    return {"schema_version": 1, "corpus_sha256": digest(corpus.read_bytes()), "seed": None,
            "method": "Exhaustive fixed mutations, one fault at a time; no random sampling.",
            "cases": cases, "summary": {
                "clean_cases": 1, "fault_cases": len(cases) - 1,
                "baseline_detected": sum(not case["baseline_pass"] for case in cases[1:]),
                "gate_detected": sum(not case["gate_pass"] for case in cases[1:]),
                "gate_false_positives": int(not cases[0]["gate_pass"]),
            }}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("examples/corpus.json"))
    parser.add_argument("--output", type=Path, default=Path("results/reproduction.json"))
    args = parser.parse_args()
    result = reproduce(args.corpus)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    result["environment"] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(),
        "revision": revision, "paid_api_cost_usd": 0, "external_api_calls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json_bytes(result))
    print(json.dumps(result["summary"], sort_keys=True))
    return 0 if all(case["gate_pass"] == case["expected_pass"] for case in result["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
