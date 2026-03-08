from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config.logging import configure_logging, log_and_translate_error
from src.config.settings import ensure_runtime_dirs
from src.services.readiness_service import ReadinessService, format_readiness_report

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anonymapp", description="AnonymApp CLI (MVP skeleton)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    anonymize = subparsers.add_parser("anonymize", help="Anonymize a TXT file")
    anonymize.add_argument(
        "--engine",
        "--backend",
        dest="engine",
        required=True,
        choices=["classic", "transformer"],
        help="Engine identifier to run (classic|transformer).",
    )
    anonymize.add_argument("--input", required=True)
    anonymize.add_argument("--output", required=False)
    anonymize.add_argument("--mapping", required=False)
    anonymize.set_defaults(handler=_handle_anonymize)

    deanonymize = subparsers.add_parser("deanonymize", help="Deanonymize using mapping")
    deanonymize.add_argument("--input", required=True)
    deanonymize.add_argument("--output", required=False)
    deanonymize.add_argument("--mapping", required=True)
    deanonymize.set_defaults(handler=_handle_deanonymize)

    readiness = subparsers.add_parser("readiness", help="Show backend readiness status")
    readiness.add_argument("--backend", choices=["classic", "transformer"], required=False)
    readiness.set_defaults(handler=_handle_readiness)

    return parser


def _normalize_paths(args: argparse.Namespace) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key in ("input", "output", "mapping"):
        value = getattr(args, key, None)
        if value:
            paths[key] = Path(value).expanduser().resolve()
    return paths


def _handle_readiness(args: argparse.Namespace) -> int:
    report = getattr(args, "_startup_readiness_report", None)
    if report is None:
        readiness_service = getattr(args, "_readiness_service", ReadinessService())
        report = readiness_service.get_readiness_report()
    if args.backend:
        report = [r for r in report if r.engine_id == args.backend]
    print(format_readiness_report(report))
    return 0


def _handle_anonymize(args: argparse.Namespace) -> int:
    from src.services.anonymization_service import run_anonymization_job

    paths = _normalize_paths(args)
    job = run_anonymization_job(
        backend=args.engine,
        input_path=paths["input"],
        output_path=paths.get("output"),
        mapping_path=paths.get("mapping"),
    )
    print(f"Engine: {args.engine}")
    print(f"Anonymized output: {job.output_path}")
    print(f"Mapping artifact: {job.mapping_path}")
    return 0


def _handle_deanonymize(args: argparse.Namespace) -> int:
    from src.services.deanonymization_service import run_deanonymization_job

    paths = _normalize_paths(args)
    job = run_deanonymization_job(
        input_path=paths["input"],
        mapping_path=paths["mapping"],
        output_path=paths.get("output"),
    )
    print(f"Origin engine: {job.engine_id}")
    print(f"Deanonymized output: {job.output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_dirs()
    configure_logging()

    parser = build_parser()
    args = parser.parse_args(argv)
    readiness_service = ReadinessService()
    startup_report = readiness_service.get_readiness_report(refresh=True)
    setattr(args, "_readiness_service", readiness_service)
    setattr(args, "_startup_readiness_report", startup_report)
    LOGGER.info("Startup readiness report:\n%s", format_readiness_report(startup_report))

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2

    try:
        return int(handler(args))
    except Exception as exc:  # pragma: no cover - exercised via integration tests
        print(log_and_translate_error(LOGGER, exc, context=f"CLI command '{args.command}'"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
