# Design decisions

## Constrained source

A structured source makes loss visible without reversing arbitrary HTML. Immutable objects hold validated values. Renderers escape syntax instead of executing source markup. The CLI always validates before rendering.

## Verification authority

A self-consistent manifest can describe corrupted content. Verification renders from the original corpus, compares exact bytes, and separately checks the manifest. Hashes identify expected and observed bytes for diagnosis. They are not signatures. The supplied corpus must itself be trusted.

## Publication semantics

Build writes to a temporary sibling directory and verifies before rename. A failed write or gate removes staging and leaves the target unpublished. Existing destinations are rejected. A deployment system can switch its own pointer after checking the release.

The destination check and rename are not a portable compare-and-swap operation. Concurrent writers and malicious parent-directory changes are outside the single-writer contract. No fsync protocol is implemented, so abrupt power loss has no durability guarantee.

## Equivalence boundary

Byte comparison detects even harmless whitespace edits. It cannot independently establish that a renderer correctly expresses the source for every consumer. HTML parser tests check literal code and cell text. Markdown tests cover escaping and fence collisions, not universal renderer interoperability.

The canonical-only baseline illustrates a specific blind spot. It is not a competitive state-of-the-art validator. The fixed corpus supports claims about the included mutations only. Search ranking, retrieval quality, model citation behavior, live-site coverage, latency, and historical client work are not measured.
