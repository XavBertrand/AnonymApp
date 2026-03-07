from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
OUTPUTS_DIR = RUNTIME_ROOT / "outputs"
MAPPINGS_DIR = RUNTIME_ROOT / "mappings"
LOGS_DIR = RUNTIME_ROOT / "logs"
TMP_CLASSIC_SCRIPT = PROJECT_ROOT / "tmp" / "anonymizer.py"
TMP_TRANSFORMER_SCRIPT = PROJECT_ROOT / "tmp" / "transformer_anonymizer.py"


@dataclass(frozen=True)
class RuntimePaths:
    runtime_root: Path = RUNTIME_ROOT
    outputs_dir: Path = OUTPUTS_DIR
    mappings_dir: Path = MAPPINGS_DIR
    logs_dir: Path = LOGS_DIR


def ensure_runtime_dirs() -> RuntimePaths:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return RuntimePaths()
