"""Command-line interface: ``incident-review-copilot review FILE...``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .report import to_json, to_markdown
from .review import review_text

EXIT_OK, EXIT_BELOW_THRESHOLD, EXIT_USAGE = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incident-review-copilot",
        description="Lint and score Markdown postmortems.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review", help="review one or more postmortem files")
    review.add_argument("files", nargs="+", metavar="FILE",
                        help="Markdown postmortem to review, or - for stdin")
    review.add_argument("--format", choices=("markdown", "json"), default="markdown",
                        help="output format (default: markdown)")
    review.add_argument("--min-score", type=int, default=70, metavar="N",
                        help="exit with status 1 if any file scores below N (default: 70)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reviews = {}
    for path in args.files:
        try:
            if path == "-":
                text, name = sys.stdin.read(), "<stdin>"
            else:
                with open(path, encoding="utf-8") as handle:
                    text, name = handle.read(), path
        except (OSError, UnicodeDecodeError) as error:
            print(f"incident-review-copilot: cannot read {path}: {error}", file=sys.stderr)
            return EXIT_USAGE
        reviews[name] = review_text(text)

    if args.format == "json":
        print(to_json(reviews, args.min_score))
    else:
        print("\n".join(to_markdown(name, review, args.min_score)
                        for name, review in reviews.items()), end="")
    passed = all(review.score >= args.min_score for review in reviews.values())
    return EXIT_OK if passed else EXIT_BELOW_THRESHOLD


if __name__ == "__main__":
    sys.exit(main())
