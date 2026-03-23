from __future__ import annotations

from pathlib import Path


def packaged_models_root(project_root: Path) -> Path:
    return project_root / "models"


def packaged_readiness(project_root: Path) -> tuple[str, str]:
    models_root = packaged_models_root(project_root)
    if not models_root.exists():
        return "blocked", f"Models directory not found: {models_root}"
    if not any(models_root.iterdir()):
        return "blocked", f"Models directory is empty: {models_root}"
    return "ready", f"Models directory available: {models_root}"


if __name__ == "__main__":  # pragma: no cover
    status, message = packaged_readiness(Path(__file__).resolve().parents[2])
    print(f"{status}: {message}")
