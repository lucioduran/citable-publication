# Citable Publication

[![CI](https://github.com/lucioduran/citable-publication/actions/workflows/ci.yml/badge.svg)](https://github.com/lucioduran/citable-publication/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Publish HTML, Markdown, and JSON from one corpus. Block release when any representation differs from its source contract.

## Problem

A correct canonical URL does not guarantee complete content. An export can lose code, truncate a table, or change its JSON schema while still pointing to the same page. This project makes those failures reproducible and checks every generated file before promoting a publication directory.

## Scope

Project 01 of the engineering evidence series. Supports English documents with literal paragraphs, code blocks, rectangular tables, and named sections. Each document has a canonical HTTPS URL and each section has a stable fragment.

There are no runtime dependencies. The included corpus contains three original synthetic documents under MIT. The design is inspired by the publication requirements of [lucioduran.com](https://lucioduran.com/en/access), but does not audit or certify the live website.

## Quick start

Install Python 3.13.7, then run:

```sh
git clone https://github.com/lucioduran/citable-publication.git
cd citable-publication
python -m citable_publication build --corpus examples/corpus.json --output dist/first-release
python -m citable_publication verify --corpus examples/corpus.json --output dist/first-release
```

Both commands print a JSON report. Successful verification exits with `0`. No account, API key, server, or paid service is required.

## Usage

Edit a copy of [examples/corpus.json](examples/corpus.json). See [docs/contract.md](docs/contract.md) for the exact input contract.

```sh
python -m citable_publication build --corpus examples/corpus.json --output dist/second-release
python -m http.server 8000 --directory dist/second-release
```

Open `http://localhost:8000/publishing-contract.html`. Corresponding `.md` and `.json` files represent the same document. `manifest.json` lists every canonical URL, file path, media type, byte count, and SHA-256 digest.

| Exit code | Meaning |
| --- | --- |
| `0` | All checks passed |
| `1` | Missing, changed, unsafe, or unexpected output files |
| `2` | Invalid input, filesystem error, or existing build destination |

Builds require a new destination directory. Use versioned directories. Save reports outside the publication directory because unexpected files intentionally fail verification.

## Architecture

```text
Source corpus -> strict validation -> immutable document model
                                         |
                      +------------------+------------------+
                      |                  |                  |
                     HTML             Markdown             JSON
                      +------------------+------------------+
                                         |
                           manifest with hashes and sizes
                                         |
                    staging directory -> verification -> rename
```

Verification regenerates expected bytes from the supplied corpus. It does not trust the generated manifest as its authority. Altering a file and its manifest hash still fails. Reports include per-document status and per-file findings. A manifest failure can reject the release even when document files pass.

See [docs/design.md](docs/design.md) for design decisions and filesystem guarantees.

## Reproduction

From the repository root:

```sh
python -m experiments.reproduce --output build/reproduction.json
```

The experiment builds the same corpus for both validators, runs a clean control, then injects six faults into each of three documents. It restores original files before every case and verifies that each mutation changed bytes.

The baseline checks only HTML canonical URLs. The full gate checks the entire publication against the source. Mutations cover canonical URLs, JSON schema versions, Markdown code, HTML tables, missing JSON, and an emptied manifest.

[Raw results](results/reproduction.json) contain every case, per-file findings, corpus hash, code revision, Python version, host platform, UTC timestamp, and API cost. No random seed is used: the matrix is exhaustive and fixed. There are no model calls or paid API costs. This measures correctness, not performance. Environment metadata may differ on reproduction; case outcomes should match.

There is no development/evaluation split because this is a fixed regression matrix, not a learned benchmark.

## Results

Recorded with Python 3.13.7 on the host identified in the raw report:

| Measurement | Canonical-only baseline | Full gate |
| --- | ---: | ---: |
| Clean controls accepted | 1 / 1 | 1 / 1 |
| Injected faults rejected | 3 / 18 | 18 / 18 |
| Injected faults missed | 15 / 18 | 0 / 18 |

The baseline misses faults that leave the canonical link intact. The full gate rejects every mutation in this fixture set. These counts are fixed test outcomes, not detection-rate estimates for arbitrary websites. No confidence interval or general improvement claim is inferred.

[Clean publication report](results/publication.json) covers all three document URLs and all ten expected files. Repeating the emptied-manifest case for each document exercises the same global failure three times; there are six fault classes, not eighteen.

## Testing

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
python -m coverage run -m unittest discover -v
python -m coverage report
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. Runtime-only tests also work with `python -m unittest discover -v`.

Tests cover malformed inputs, escaping, literal code and table preservation, citation URLs, manifest completeness, content drift, symlinks, staging cleanup, existing destination protection, CLI reports and exit codes, and the experiment matrix. CI runs on Linux, macOS, and Windows with a 90% combined statement/branch coverage gate. Development tools and CI actions are pinned.

## Limitations

- Exact byte comparison rejects harmless manual formatting changes too.
- The verifier and renderer share code. Independent HTML parser assertions test representative content, but the gate alone cannot detect a shared rendering bug.
- Markdown uses GFM-style tables and HTML anchors. Consumer support varies. A separator newline after code payloads can appear as an extra trailing blank line.
- This is a constrained document model. Rich inline text, images, lists, nested tables, and multilingual documents are unsupported.
- SHA-256 identifies bytes, not authorship, factual truth, or a trusted source.
- Publication requires a trusted single-writer filesystem. Staging is not a concurrent deployment lock or a power-loss durability guarantee. Serving and cache invalidation are outside scope.
- The corpus is loaded into memory. Untrusted uploads need external size limits. `language: en` is a declaration, not natural-language detection.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Include regression tests and document contract changes. Use focused commits and the shared README structure. Report vulnerabilities using [SECURITY.md](SECURITY.md).

## License

Code, original corpus fixtures, documentation, and recorded results use the [MIT license](LICENSE). External websites retain their own terms and are not redistributed here. Python and development tools retain their upstream licenses.
