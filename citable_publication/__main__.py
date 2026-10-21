"""Command-line publication and verification."""

import argparse
import json
import sys
from pathlib import Path

from .model import PublicationError, load_corpus
from .publish import build, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and verify equivalent document representations."
    )
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        documents = load_corpus(args.corpus)
        report = (build if args.command == "build" else verify)(documents, args.output)
    except (PublicationError, OSError) as error:
        print(json.dumps({"passed": False, "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
