from __future__ import annotations

from pathlib import Path


def build_portable_distribution(project_root: Path) -> Path:
    """Return the expected portable build directory for local packaging flows."""
    return project_root / "dist" / "a4_desktop_portable"


if __name__ == "__main__":  # pragma: no cover
    print(build_portable_distribution(Path(__file__).resolve().parents[2]))
