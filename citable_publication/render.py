"""Render the supported document model without executing source markup."""

from hashlib import sha256
from html import escape
import json
import re

from .model import Block, Document


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _literal(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", escape(text, quote=False))


def _html_block(block: Block) -> str:
    if block.kind == "paragraph":
        return f"<p>{escape(block.text)}</p>"
    if block.kind == "code":
        return f'<pre><code class="language-{block.language}">{escape(block.text)}</code></pre>'
    headers = "".join(f'<th scope="col">{escape(cell)}</th>' for cell in block.headers)
    rows = "".join("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in block.rows)
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"


def render_html(document: Document) -> bytes:
    parts = [
        '<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{escape(document.title)}</title>',
        f'<link rel="canonical" href="{escape(document.canonical, quote=True)}">',
        '</head>', '<body>', '<main>', f'<h1>{escape(document.title)}</h1>',
    ]
    for section in document.sections:
        parts.extend([f'<section id="{section.id}">', f'<h2>{escape(section.title)}</h2>'])
        parts.extend(_html_block(block) for block in section.blocks)
        parts.append('</section>')
    parts.extend(['</main>', '</body>', '</html>'])
    return ("\n".join(parts) + "\n").encode("utf-8")


def _markdown_block(block: Block) -> str:
    if block.kind == "paragraph":
        return _literal(block.text)
    if block.kind == "code":
        fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", block.text)), default=0))
        # The separator newline is outside the source payload, even if it ends in a newline.
        return f"{fence}{block.language}\n{block.text}\n{fence}"
    def row(cells: tuple[str, ...]) -> str:
        return "| " + " | ".join(_literal(cell) for cell in cells) + " |"
    return "\n".join([row(block.headers), row(tuple("---" for _ in block.headers)).replace("\\-", "-"),
                       *(row(cells) for cells in block.rows)])


def render_markdown(document: Document) -> bytes:
    parts = [f'# {_literal(document.title)}', f'Canonical: <{document.canonical}>']
    for section in document.sections:
        parts.extend([f'<a id="{section.id}"></a>', f'## {_literal(section.title)}'])
        parts.extend(_markdown_block(block) for block in section.blocks)
    return ("\n\n".join(parts) + "\n").encode("utf-8")


def render_json(document: Document) -> bytes:
    value = document.to_dict()
    value["citations"] = [
        {"id": section.id, "url": f"{document.canonical}#{section.id}", "title": section.title}
        for section in document.sections
    ]
    return json_bytes(value)


def render_files(documents: tuple[Document, ...]) -> dict[str, bytes]:
    files = {}
    entries = []
    for document in documents:
        representations = {}
        for extension, content, media_type in (
            ("html", render_html(document), "text/html"),
            ("md", render_markdown(document), "text/markdown"),
            ("json", render_json(document), "application/json"),
        ):
            path = f"{document.slug}.{extension}"
            files[path] = content
            representations[extension] = {"path": path, "sha256": digest(content), "bytes": len(content), "media_type": media_type}
        entries.append({"canonical": document.canonical, "slug": document.slug, "representations": representations})
    files["manifest.json"] = json_bytes({"schema_version": 1, "documents": entries})
    return files
