from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ALL_BACKENDS = ("transformer",)


@dataclass(frozen=True)
class ModelCheckResult:
    model_name: str
    required: bool
    available: bool
    message: str
    remediation: str | None = None
    backends: tuple[str, ...] = ALL_BACKENDS


def _huggingface_cache_candidates(model_name: str, hf_home: Path) -> list[Path]:
    hub_dir = hf_home / "hub"
    normalized = model_name.strip().replace("/", "--")
    return [
        hub_dir / f"models--{normalized}",
        hub_dir / normalized,
    ]


def check_model_path(
    model_name: str,
    *,
    required: bool = True,
    backends: tuple[str, ...] = ALL_BACKENDS,
    env_override_var: str | None = None,
) -> ModelCheckResult:
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    candidates: list[Path] = []
    override_is_explicit = False

    if env_override_var:
        override = os.environ.get(env_override_var, "").strip()
        if override:
            candidates.append(Path(override).expanduser())
            override_is_explicit = True

    if not override_is_explicit:
        candidates.extend(_huggingface_cache_candidates(model_name, hf_home))

    for candidate in candidates:
        if candidate.exists():
            return ModelCheckResult(
                model_name,
                required,
                True,
                f"model available at {candidate}",
                backends=backends,
            )

    expected = ", ".join(str(path) for path in candidates)
    return ModelCheckResult(
        model_name,
        required,
        False,
        f"model missing (checked: {expected})",
        f"Provision model assets for '{model_name}' before enabling this backend.",
        backends=backends,
    )


def run_model_checks() -> list[ModelCheckResult]:
    checks = [
        check_model_path(
            "urchade/gliner_multi_pii-v1",
            required=True,
            backends=("transformer",),
            env_override_var="ANONYMAPP_TRANSFORMER_MODEL_PATH",
        ),
    ]
    return checks
