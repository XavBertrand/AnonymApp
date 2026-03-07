from __future__ import annotations

import importlib
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyCheckResult:
    name: str
    required: bool
    available: bool
    message: str
    remediation: str | None = None


def check_python_module(module_name: str, required: bool = True) -> DependencyCheckResult:
    try:
        importlib.import_module(module_name)
        return DependencyCheckResult(module_name, required, True, "available")
    except Exception:
        remediation = f"Install missing module '{module_name}' in project environment."
        return DependencyCheckResult(module_name, required, False, "missing", remediation)


def check_ollama_endpoint(host: str = "localhost", port: int = 11434) -> DependencyCheckResult:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect((host, port))
        return DependencyCheckResult("ollama", False, True, "reachable")
    except OSError:
        return DependencyCheckResult(
            "ollama",
            False,
            False,
            "unavailable (optional)",
            "Start Ollama service only if optional QC is needed.",
        )
    finally:
        sock.close()


def run_dependency_checks() -> list[DependencyCheckResult]:
    checks = [
        check_python_module("transformers", required=True),
        check_python_module("torch", required=True),
        check_python_module("rapidfuzz", required=True),
        check_python_module("unidecode", required=True),
        check_python_module("gliner", required=False),
        check_python_module("requests", required=False),
        check_ollama_endpoint(),
    ]
    return checks
