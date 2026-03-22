from __future__ import annotations

from pathlib import Path


def packaged_models_root(project_root: Path) -> Path:
    return project_root / "models"


if __name__ == "__main__":  # pragma: no cover
    print(packaged_models_root(Path(__file__).resolve().parents[2]))
