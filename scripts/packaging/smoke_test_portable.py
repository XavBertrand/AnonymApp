from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.packaging.build_windows_portable import (
    PORTABLE_EXECUTABLE_NAME,
    PORTABLE_LAUNCHER_NAME,
    launcher_script_content,
    portable_build_plan,
)
from src.adapters.persistence.artifact_store import ArtifactStore
from src.config.desktop_settings import recommended_windows_data_root, recommended_windows_export_root


@dataclass(frozen=True)
class PortableRuntimePaths:
    app_root: Path
    models_root: Path
    data_root: Path
    exports_root: Path


def packaged_models_root(project_root: Path) -> Path:
    return project_root / "models"


def packaged_readiness(project_root: Path) -> tuple[str, str]:
    models_root = packaged_models_root(project_root)
    if not models_root.exists():
        return "blocked", f"Models directory not found: {models_root}"
    if not any(models_root.iterdir()):
        return "blocked", f"Models directory is empty: {models_root}"
    return "ready", f"Models directory available: {models_root}"


def portable_runtime_paths(
    extracted_root: Path,
    *,
    local_appdata_root: Path | None = None,
    user_home_root: Path | None = None,
) -> PortableRuntimePaths:
    app_root = extracted_root.resolve()
    local_root = (local_appdata_root or extracted_root / "portable-user" / "AppData" / "Local").resolve()
    user_root = (user_home_root or extracted_root / "portable-user").resolve()
    return PortableRuntimePaths(
        app_root=app_root,
        models_root=packaged_models_root(app_root),
        data_root=recommended_windows_data_root(local_root),
        exports_root=recommended_windows_export_root(user_root),
    )


def validate_portable_relative_path_resolution(extracted_root: Path) -> tuple[str, str]:
    paths = portable_runtime_paths(extracted_root)
    if paths.models_root.parent != paths.app_root:
        return "blocked", "Packaged models are not resolved relative to the extracted application root."
    return "ready", f"Models resolve relative to the extracted root: {paths.models_root}"


def validate_export_location_resolution(extracted_root: Path) -> tuple[str, str]:
    paths = portable_runtime_paths(extracted_root)
    store = ArtifactStore(paths.data_root / "cases", paths.exports_root)
    export_path = store.deanonymized_export_path("case1234", "Dossier Test", "session1234", "export1234")
    case_root = store.case_root("case1234", "Dossier Test")
    if case_root in export_path.parents:
        return "blocked", "User-facing exports must not be written inside the case-managed working directory."
    return "ready", f"Deanonymized exports resolve to a user-facing directory: {export_path}"


def validate_regenerated_artifact_naming(extracted_root: Path) -> tuple[str, str]:
    paths = portable_runtime_paths(extracted_root)
    store = ArtifactStore(paths.data_root / "cases", paths.exports_root)
    regenerated_output = store.regenerated_output_path("case1234", "Dossier Test", "piece.txt", "action1234")
    regenerated_mapping = store.regenerated_mapping_path("case1234", "Dossier Test", "piece.txt", "action1234")
    if "-review-" not in regenerated_output.name or regenerated_output.suffix != ".txt":
        return "blocked", f"Unexpected regenerated output naming: {regenerated_output.name}"
    if "-review-" not in regenerated_mapping.name or regenerated_mapping.suffix != ".json":
        return "blocked", f"Unexpected regenerated mapping naming: {regenerated_mapping.name}"
    return "ready", f"Regenerated artifacts keep stable review naming: {regenerated_output.name}"


def validate_deanonymized_export_paths(extracted_root: Path) -> tuple[str, str]:
    paths = portable_runtime_paths(extracted_root)
    store = ArtifactStore(paths.data_root / "cases", paths.exports_root)
    export_path = store.deanonymized_export_path("case1234", "Dossier Test", "session1234", "export1234")
    if export_path.suffix != ".txt" or "deanonymized-" not in export_path.name:
        return "blocked", f"Unexpected deanonymized export naming: {export_path.name}"
    return "ready", f"Deanonymized exports use portable TXT-friendly paths: {export_path}"


def validate_extracted_folder_execution(extracted_root: Path) -> tuple[str, str]:
    plan = portable_build_plan(extracted_root)
    launcher_text = launcher_script_content(extracted_root)
    readiness_state, readiness_message = packaged_readiness(extracted_root)
    if readiness_state != "ready":
        return readiness_state, readiness_message
    if plan.executable_path.name != PORTABLE_EXECUTABLE_NAME:
        return "blocked", f"Unexpected portable executable name: {plan.executable_path.name}"
    if PORTABLE_LAUNCHER_NAME not in str(plan.launcher_path):
        return "blocked", f"Unexpected launcher path: {plan.launcher_path}"
    if "set PORTABLE_ROOT=%~dp0" not in launcher_text:
        return "blocked", "Portable launcher does not anchor execution to the extracted folder."
    return "ready", f"Portable execution remains extracted-folder safe: {plan.bundle_root}"


def portable_smoke_report(extracted_root: Path) -> dict[str, tuple[str, str]]:
    return {
        "readiness": packaged_readiness(extracted_root),
        "relative_models": validate_portable_relative_path_resolution(extracted_root),
        "export_location": validate_export_location_resolution(extracted_root),
        "regenerated_naming": validate_regenerated_artifact_naming(extracted_root),
        "deanonymized_export": validate_deanonymized_export_paths(extracted_root),
        "extracted_execution": validate_extracted_folder_execution(extracted_root),
    }


if __name__ == "__main__":  # pragma: no cover
    report = portable_smoke_report(REPO_ROOT)
    status = "ready" if all(item[0] == "ready" for item in report.values()) else "blocked"
    message = "; ".join(f"{name}={state}" for name, (state, _detail) in report.items())
    print(f"{status}: {message}")
