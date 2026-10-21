"""Verify every expected byte before promoting a new publication directory."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile

from .model import Document, PublicationError
from .render import digest, render_files


@dataclass(frozen=True)
class Finding:
    path: str
    status: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None

    def to_dict(self) -> dict:
        return vars(self)


def verify(documents: tuple[Document, ...], directory: Path) -> dict:
    expected = render_files(documents)
    findings = []
    if directory.is_symlink() or not directory.is_dir():
        raise PublicationError("Publication must be a real directory")
    actual = {path.relative_to(directory).as_posix(): path for path in directory.rglob("*")}
    for name, content in expected.items():
        path = actual.pop(name, None)
        expected_hash = digest(content)
        if path is None:
            findings.append(Finding(name, "missing", expected_hash))
        elif path.is_symlink() or not path.is_file():
            findings.append(Finding(name, "unsafe", expected_hash))
        else:
            try:
                actual_content = path.read_bytes()
                findings.append(Finding(name, "pass" if actual_content == content else "mismatch",
                                        expected_hash, digest(actual_content)))
            except OSError:
                findings.append(Finding(name, "unreadable", expected_hash))
    findings.extend(Finding(name, "unexpected") for name in sorted(actual))
    return {
        "schema_version": 1,
        "passed": all(item.status == "pass" for item in findings),
        "documents": [
            {"canonical": doc.canonical, "slug": doc.slug,
             "passed": all(item.status == "pass" for item in findings if item.path in
                           {f"{doc.slug}.{ext}" for ext in ("html", "md", "json")})}
            for doc in documents
        ],
        "files": [item.to_dict() for item in findings],
    }


def build(documents: tuple[Document, ...], destination: Path) -> dict:
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise PublicationError("Destination already exists; choose a new release directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        for name, content in render_files(documents).items():
            (staging / name).write_bytes(content)
        report = verify(documents, staging)
        if not report["passed"]:
            raise PublicationError("Publication verification failed; nothing was promoted")
        # The sibling staging directory keeps promotion on the same filesystem.
        if destination.exists() or destination.is_symlink():
            raise PublicationError("Destination appeared during publication")
        os.rename(staging, destination)
        return report
    finally:
        if staging.exists():
            shutil.rmtree(staging)
