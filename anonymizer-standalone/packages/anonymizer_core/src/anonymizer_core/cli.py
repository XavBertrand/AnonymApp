"""Standalone anonymizer CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anonymizer_core.errors import AnonymizationError, InputValidationError
from anonymizer_core.models import BatchRequest
from anonymizer_core.policy import STRICT_OFFLINE_POLICY_NAME, load_policy
from anonymizer_core.service import DocumentAnonymizer
from anonymizer_core.storage.mapping_store import MappingStore, resolve_placeholder_reverse

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".xlsx", ".txt")


def _discover_inputs(input_arg: Path) -> tuple[Path, list[Path]]:
    if input_arg.is_file():
        if input_arg.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise InputValidationError(f"Unsupported format: {input_arg.suffix}")
        return input_arg.parent, [input_arg]

    if not input_arg.exists():
        raise InputValidationError(f"Input path does not exist: {input_arg}")

    files: list[Path] = []
    for path in sorted(input_arg.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    if not files:
        raise InputValidationError("No supported input files found")
    return input_arg, files


def _apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for source in sorted(replacements.keys(), key=len, reverse=True):
        text = text.replace(source, replacements[source])
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone offline document anonymizer")
    sub = parser.add_subparsers(dest="command", required=True)

    anon = sub.add_parser("anonymize", help="Batch anonymize input files into flat .txt outputs")
    anon.add_argument("--input", required=True, help="Input file or directory")
    anon.add_argument("--output", required=True, help="Output directory")
    anon.add_argument("--case-id", required=True, help="Case identifier")
    anon.add_argument(
        "--policy",
        default=STRICT_OFFLINE_POLICY_NAME,
        choices=(STRICT_OFFLINE_POLICY_NAME,),
        help="Execution policy (strict_offline only)",
    )
    anon.add_argument(
        "--report",
        default=None,
        help="Report path (default: <output>/report.json)",
    )
    anon.add_argument("--config", default=None, help="Optional policy config file")
    anon.add_argument("--fail-fast", action="store_true", help="Stop on first file failure")
    anon.add_argument("--concat", action="store_true", help="Write one concatenated output file")
    anon.add_argument(
        "--concat-filename",
        default="anonymized_all.txt",
        help="Concatenated output filename (inside output directory)",
    )

    dean = sub.add_parser("deanonymize", help="Replace placeholders using local mapping")
    dean.add_argument("--mapping", required=True, help="Path to mapping.json")
    dean.add_argument("--text-file", default=None, help="Input text file to deanonymize")
    dean.add_argument("--text-stdin", action="store_true", help="Read anonymized text from stdin")
    dean.add_argument("--output", required=True, help="Output text file path")

    return parser


def _run_anonymize(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve() if args.report else (output_root / "report.json")
    config_path = Path(args.config).expanduser().resolve() if args.config else None

    input_root, inputs = _discover_inputs(input_path)
    policy = load_policy(args.policy, config_path)
    service = DocumentAnonymizer()

    result = service.anonymize_batch(
        BatchRequest(
            case_id=args.case_id,
            policy_name=args.policy,
            policy=policy,
            input_root=input_root,
            input_paths=inputs,
            output_root=output_root,
            report_path=report_path,
            continue_on_error=not args.fail_fast,
            concat_output=bool(args.concat),
            concat_filename=str(args.concat_filename),
        )
    )

    print(f"Anonymization completed: {result.status}")
    print(f"Report: {result.report_path}")
    print(f"Mapping: {result.mapping_path}")
    if result.concat_output_path:
        print(f"Concat: {result.concat_output_path}")
    return 0 if result.totals["failed"] == 0 else 10


def _run_deanonymize(args: argparse.Namespace) -> int:
    mapping_path = Path(args.mapping).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if bool(args.text_file) == bool(args.text_stdin):
        raise InputValidationError("Use exactly one of --text-file or --text-stdin")

    if args.text_file:
        source_text = Path(args.text_file).expanduser().resolve().read_text(encoding="utf-8")
    else:
        source_text = sys.stdin.read()

    payload = MappingStore().read_mapping(mapping_path)
    reverse = resolve_placeholder_reverse(payload)
    restored = _apply_replacements(source_text, reverse)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(restored, encoding="utf-8")

    summary = {
        "mapping": str(mapping_path),
        "output": str(output_path),
        "replacements": len(reverse),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "anonymize":
            return _run_anonymize(args)
        if args.command == "deanonymize":
            return _run_deanonymize(args)
        raise InputValidationError("Unknown command")
    except AnonymizationError as exc:
        print(f"ERROR {exc.code}: {exc.message_safe}")
        return 40 if exc.code == "SECURITY_POLICY_ERROR" else 20


if __name__ == "__main__":
    raise SystemExit(main())
