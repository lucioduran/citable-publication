# Source contract

The root object has exactly `schema_version: 1` and a nonempty `documents` array. Unknown fields and duplicate JSON keys fail validation.

| Document field | Constraint |
| --- | --- |
| `schema_version` | Integer `1`; booleans rejected |
| `slug` | Unique lowercase ASCII slug starting with a letter |
| `canonical` | Unique absolute HTTPS URL without credentials, query, or fragment |
| `title` | Nonempty single-line text |
| `language` | Exactly `en` |
| `sections` | Nonempty array |

A section has exactly `id`, `title`, and `blocks`. IDs use the slug grammar and must be unique within a document. Titles are nonempty single-line text. Blocks must be a nonempty array.

| Block type | Required fields |
| --- | --- |
| `paragraph` | `type`, nonempty single-line `text` |
| `code` | `type`, slug-shaped `language`, nonempty multiline `text` |
| `table` | `type`, nonempty string array `headers`, array `rows` |

Rows must match the header width. Cells must be nonempty single-line strings. Tables may have zero data rows. Code preserves tabs and LF newlines. Other control characters, invalid Unicode scalars, and em dashes are rejected. Unicode is retained without normalization.

JSON output adds `citations` with each section's ID, title, and URL. It is an output representation, not a source document unless that field is removed. The source remains the verification authority.

Example canonical URLs are synthetic identifiers. The publisher does not fetch them or test HTTP availability.

Document slugs cannot be `manifest` or Windows device names (`con`, `prn`, `aux`,
`nul`, `com1` through `com9`, or `lpt1` through `lpt9`). This prevents manifest
collisions and keeps output filenames portable across supported systems.
