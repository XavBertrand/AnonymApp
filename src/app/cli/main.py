from __future__ import annotations

import argparse
from pathlib import Path

from src.config.logging import configure_logging
from src.config.settings import ensure_runtime_dirs
from src.services.readiness_service import format_readiness_report, get_readiness_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anonymapp", description="AnonymApp CLI (MVP skeleton)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    anonymize = subparsers.add_parser("anonymize", help="Anonymize a TXT file")
    anonymize.add_argument("--backend", required=True, choices=["classic", "transformer"])
    anonymize.add_argument("--input", required=True)
    anonymize.add_argument("--output", required=True)
    anonymize.add_argument("--mapping", required=True)

    deanonymize = subparsers.add_parser("deanonymize", help="Deanonymize using mapping")
    deanonymize.add_argument("--backend", required=True, choices=["classic", "transformer"])
    deanonymize.add_argument("--input", required=True)
    deanonymize.add_argument("--output", required=True)
    deanonymize.add_argument("--mapping", required=True)

    readiness = subparsers.add_parser("readiness", help="Show backend readiness status")
    readiness.add_argument("--backend", choices=["classic", "transformer"], required=False)

    return parser


def _normalize_paths(args: argparse.Namespace) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key in ("input", "output", "mapping"):
        value = getattr(args, key, None)
        if value:
            paths[key] = Path(value).expanduser().resolve()
    return paths


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_dirs()
    configure_logging()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "readiness":
        report = get_readiness_report()
        if args.backend:
            report = [r for r in report if r.engine_id == args.backend]
        print(format_readiness_report(report))
        return 0

    paths = _normalize_paths(args)
    print(
        f"CLI skeleton only. command={args.command}, backend={args.backend}, "
        f"paths={{'input': '{paths.get('input')}', 'output': '{paths.get('output')}', 'mapping': '{paths.get('mapping')}'}}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
