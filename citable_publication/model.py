"""Validate the versioned document contract before rendering."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class PublicationError(ValueError):
    pass


def _object(value: object, keys: set[str], location: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise PublicationError(f"{location}: expected fields {sorted(keys)}")
    return value


def _text(value: object, location: str, *, multiline: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationError(f"{location}: expected nonempty text")
    if any(ord(c) < 32 and not (multiline and c in "\n\t") for c in value):
        raise PublicationError(f"{location}: unsupported control character")
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise PublicationError(f"{location}: invalid Unicode scalar")
    if chr(0x2014) in value:
        raise PublicationError(f"{location}: em dashes are not allowed")
    return value


def _identifier(value: object, location: str) -> str:
    value = _text(value, location)
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value):
        raise PublicationError(f"{location}: expected a lowercase slug")
    return value


def _url(value: object) -> str:
    value = _text(value, "canonical")
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.port not in (None, 443)
            or url.username
            or url.password
            or url.query
            or url.fragment
            or any(c.isspace() or c in '<>"\\' for c in value)
        ):
            raise ValueError
    except ValueError as error:
        raise PublicationError(
            "canonical: expected an absolute HTTPS URL without credentials, query, or fragment"
        ) from error
    return value


@dataclass(frozen=True)
class Block:
    kind: str
    text: str = ""
    language: str = ""
    headers: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()

    def to_dict(self) -> dict:
        if self.kind == "paragraph":
            return {"type": self.kind, "text": self.text}
        if self.kind == "code":
            return {"type": self.kind, "language": self.language, "text": self.text}
        return {
            "type": self.kind,
            "headers": list(self.headers),
            "rows": [list(row) for row in self.rows],
        }


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    blocks: tuple[Block, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True)
class Document:
    slug: str
    canonical: str
    title: str
    sections: tuple[Section, ...]

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "slug": self.slug,
            "canonical": self.canonical,
            "title": self.title,
            "language": "en",
            "sections": [section.to_dict() for section in self.sections],
        }


def _block(value: object) -> Block:
    if not isinstance(value, dict):
        raise PublicationError("block: expected an object")
    kind = value.get("type")
    if kind == "paragraph":
        _object(value, {"type", "text"}, "paragraph")
        return Block(kind, text=_text(value["text"], "paragraph.text"))
    if kind == "code":
        _object(value, {"type", "language", "text"}, "code")
        return Block(
            kind,
            text=_text(value["text"], "code.text", multiline=True),
            language=_identifier(value["language"], "code.language"),
        )
    if kind == "table":
        _object(value, {"type", "headers", "rows"}, "table")
        headers, rows = value["headers"], value["rows"]
        if not isinstance(headers, list) or not headers or not isinstance(rows, list):
            raise PublicationError("table: expected nonempty headers and a row list")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(headers):
                raise PublicationError("table: row width must equal header width")
        return Block(
            kind,
            headers=tuple(_text(cell, "table.header") for cell in headers),
            rows=tuple(tuple(_text(cell, "table.cell") for cell in row) for row in rows),
        )
    raise PublicationError("block: unsupported type")


def parse_document(value: object) -> Document:
    value = _object(
        value, {"schema_version", "slug", "canonical", "title", "language", "sections"}, "document"
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise PublicationError("document: unsupported schema version")
    if value["language"] != "en":
        raise PublicationError("document: language must be en")
    if not isinstance(value["sections"], list) or not value["sections"]:
        raise PublicationError("document: expected nonempty sections")
    sections = []
    ids: set[str] = set()
    for section in value["sections"]:
        section = _object(section, {"id", "title", "blocks"}, "section")
        identifier = _identifier(section["id"], "section.id")
        if identifier in ids:
            raise PublicationError("section: duplicate id")
        ids.add(identifier)
        if not isinstance(section["blocks"], list) or not section["blocks"]:
            raise PublicationError("section: expected nonempty blocks")
        sections.append(
            Section(
                identifier,
                _text(section["title"], "section.title"),
                tuple(_block(block) for block in section["blocks"]),
            )
        )
    slug = _identifier(value["slug"], "slug")
    reserved = {"manifest", "con", "prn", "aux", "nul"}
    reserved.update(f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10))
    if slug in reserved:
        raise PublicationError("slug: reserved publication or operating-system filename")
    return Document(
        slug,
        _url(value["canonical"]),
        _text(value["title"], "title"),
        tuple(sections),
    )


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"JSON: duplicate key {key}")
        result[key] = value
    return result


def load_corpus(path: Path) -> tuple[Document, ...]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PublicationError(f"Cannot read corpus: {error}") from error
    value = _object(value, {"schema_version", "documents"}, "corpus")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise PublicationError("corpus: unsupported schema version")
    if not isinstance(value["documents"], list) or not value["documents"]:
        raise PublicationError("corpus: expected nonempty documents")
    documents = tuple(parse_document(item) for item in value["documents"])
    if len({doc.slug for doc in documents}) != len(documents):
        raise PublicationError("corpus: duplicate slug")
    if len({doc.canonical for doc in documents}) != len(documents):
        raise PublicationError("corpus: duplicate canonical URL")
    return documents
