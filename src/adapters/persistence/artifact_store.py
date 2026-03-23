from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from src.config.desktop_settings import DESKTOP_CASES_ROOT, DESKTOP_EXPORT_ROOT, ensure_desktop_dirs


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in cleaned.split("-") if part) or "case"


class ArtifactStore:
    def __init__(self, cases_root: Path | None = None, exports_root: Path | None = None) -> None:
        ensure_desktop_dirs()
        self._cases_root = cases_root or DESKTOP_CASES_ROOT
        self._exports_root = exports_root or DESKTOP_EXPORT_ROOT

    def case_root(self, case_id: str, display_name: str) -> Path:
        return self._cases_root / f"{_slugify(display_name)}-{case_id[:8]}"

    def ensure_case_dirs(self, case_id: str, display_name: str) -> dict[str, Path]:
        root = self.case_root(case_id, display_name)
        paths = {
            "root": root,
            "imports": root / "imports",
            "outputs": root / "outputs",
            "mappings": root / "mappings",
            "sessions": root / "sessions",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths

    def import_copy(self, case_id: str, display_name: str, source_path: Path) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        destination = dirs["imports"] / f"{source_path.stem}-{self.fingerprint(source_path)[:8]}{source_path.suffix}"
        shutil.copy2(source_path, destination)
        return destination

    def output_path(self, case_id: str, display_name: str, source_path: Path, job_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        fingerprint = self.fingerprint(source_path)[:8]
        return dirs["outputs"] / f"{source_path.stem}-{fingerprint}-{job_id[:8]}.anon.txt"

    def mapping_path(self, case_id: str, display_name: str, source_path: Path, job_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        fingerprint = self.fingerprint(source_path)[:8]
        return dirs["mappings"] / f"{source_path.stem}-{fingerprint}-{job_id[:8]}.mapping.json"

    def regenerated_output_path(self, case_id: str, display_name: str, source_filename: str, action_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        stem = Path(source_filename).stem
        return dirs["outputs"] / f"{stem}-review-{action_id[:8]}.anon.txt"

    def regenerated_mapping_path(self, case_id: str, display_name: str, source_filename: str, action_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        stem = Path(source_filename).stem
        return dirs["mappings"] / f"{stem}-review-{action_id[:8]}.mapping.json"

    def deanonymization_input_path(self, case_id: str, display_name: str, session_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        return dirs["sessions"] / f"pasted-{session_id[:8]}.input.txt"

    def deanonymization_result_path(self, case_id: str, display_name: str, session_id: str) -> Path:
        dirs = self.ensure_case_dirs(case_id, display_name)
        return dirs["sessions"] / f"pasted-{session_id[:8]}.result.txt"

    def deanonymized_export_path(self, case_id: str, display_name: str, session_id: str) -> Path:
        export_root = self._exports_root / f"{_slugify(display_name)}-{case_id[:8]}"
        export_root.mkdir(parents=True, exist_ok=True)
        return export_root / f"deanonymized-{session_id[:8]}.txt"

    @staticmethod
    def fingerprint(source_path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(source_path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def file_sha256(path: Path) -> str:
        return ArtifactStore.fingerprint(path)
