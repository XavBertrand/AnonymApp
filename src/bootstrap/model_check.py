from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelCheckResult:
    model_name: str
    required: bool
    available: bool
    message: str
    remediation: str | None = None


def check_model_path(model_name: str, path: Path, required: bool = True) -> ModelCheckResult:
    exists = path.exists()
    if exists:
        return ModelCheckResult(model_name, required, True, f"model available at {path}")
    return ModelCheckResult(
        model_name,
        required,
        False,
        f"model missing at {path}",
        f"Provision model assets for '{model_name}' before enabling this backend.",
    )


def run_model_checks() -> list[ModelCheckResult]:
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    checks = [
        check_model_path("camembert-ner", hf_home / "hub", required=True),
        check_model_path("gliner_multi_pii-v1", hf_home / "hub", required=False),
    ]
    return checks
