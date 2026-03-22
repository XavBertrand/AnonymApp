from __future__ import annotations

import importlib
import socket
from dataclasses import dataclass


ALL_BACKENDS = ("transformer",)


@dataclass(frozen=True)
class DependencyCheckResult:
    name: str
    required: bool
    available: bool
    message: str
    remediation: str | None = None
    backends: tuple[str, ...] = ALL_BACKENDS


def check_python_module(
    module_name: str,
    *,
    required: bool = True,
    backends: tuple[str, ...] = ALL_BACKENDS,
) -> DependencyCheckResult:
    try:
        importlib.import_module(module_name)
        return DependencyCheckResult(module_name, required, True, "available", backends=backends)
    except Exception:
        remediation = (
            f"Install missing module '{module_name}' in the project environment and rerun readiness."
            if required
            else f"Install optional module '{module_name}' to enable related optional features."
        )
        message = "missing" if required else "missing (optional)"
        return DependencyCheckResult(
            module_name,
            required,
            False,
            message,
            remediation,
            backends=backends,
        )


def check_cpu_only_compatibility(*, backends: tuple[str, ...] = ALL_BACKENDS) -> DependencyCheckResult:
    return DependencyCheckResult(
        "cpu_only_compatibility",
        True,
        True,
        "CPU-only mode is supported and does not require GPU acceleration.",
        backends=backends,
    )


def check_ollama_endpoint(
    host: str = "localhost",
    port: int = 11434,
    *,
    backends: tuple[str, ...] = ("classic",),
) -> DependencyCheckResult:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect((host, port))
        return DependencyCheckResult("ollama", False, True, "reachable (optional)", backends=backends)
    except OSError:
        return DependencyCheckResult(
            "ollama",
            False,
            False,
            "unavailable (optional)",
            "Start Ollama service only if optional QC is needed.",
            backends=backends,
        )
    finally:
        sock.close()


def run_dependency_checks() -> list[DependencyCheckResult]:
    checks = [
        check_python_module("transformers", required=True, backends=("transformer",)),
        check_python_module("torch", required=True, backends=("transformer",)),
        check_python_module("rapidfuzz", required=True, backends=("transformer",)),
        check_python_module("unidecode", required=True, backends=("transformer",)),
        check_python_module("gliner", required=True, backends=("transformer",)),
        check_cpu_only_compatibility(backends=("transformer",)),
    ]
    return checks
