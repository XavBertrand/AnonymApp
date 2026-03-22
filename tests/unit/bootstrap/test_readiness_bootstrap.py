from __future__ import annotations

from pathlib import Path

from src.bootstrap.dependency_check import DependencyCheckResult
from src.bootstrap.model_check import ModelCheckResult, run_model_checks
from src.bootstrap.readiness_bootstrap import build_backend_descriptors


def test_check_python_module_missing_required_has_remediation(monkeypatch) -> None:
    from src.bootstrap import dependency_check

    def _fake_import(module_name: str):
        raise ModuleNotFoundError(module_name)

    monkeypatch.setattr(dependency_check.importlib, "import_module", _fake_import)

    result = dependency_check.check_python_module(
        "transformers",
        required=True,
        backends=("transformer",),
    )

    assert result.available is False
    assert result.required is True
    assert "Install missing module 'transformers'" in (result.remediation or "")


def test_check_ollama_endpoint_is_optional_non_blocking(monkeypatch) -> None:
    from src.bootstrap import dependency_check

    class _FailingSocket:
        def settimeout(self, timeout: float) -> None:
            _ = timeout

        def connect(self, address: tuple[str, int]) -> None:
            _ = address
            raise OSError("connection refused")

        def close(self) -> None:
            return None

    monkeypatch.setattr(dependency_check.socket, "socket", lambda *_args, **_kwargs: _FailingSocket())
    result = dependency_check.check_ollama_endpoint()

    assert result.required is False
    assert result.available is False
    assert "optional" in result.message.lower()
    assert "Ollama" in (result.remediation or "")


def test_run_model_checks_uses_backend_model_paths(monkeypatch, tmp_path: Path) -> None:
    transformer_model_dir = tmp_path / "missing-transformer-model"

    monkeypatch.setenv("ANONYMAPP_TRANSFORMER_MODEL_PATH", str(transformer_model_dir))

    checks = run_model_checks()
    by_name = {item.model_name: item for item in checks}

    transformer = by_name["urchade/gliner_multi_pii-v1"]

    assert transformer.available is False
    assert transformer.backends == ("transformer",)
    assert "Provision model assets" in (transformer.remediation or "")


def test_readiness_status_transitions_ready_degraded_unavailable(monkeypatch) -> None:
    dependency_checks = [
        DependencyCheckResult(
            "transformers",
            required=True,
            available=True,
            message="available",
            backends=("transformer",),
        ),
        DependencyCheckResult(
            "torch",
            required=True,
            available=True,
            message="available",
            backends=("transformer",),
        ),
        DependencyCheckResult(
            "cpu_only_compatibility",
            required=True,
            available=True,
            message="CPU-only mode is supported and does not require GPU acceleration.",
            backends=("transformer",),
        ),
        DependencyCheckResult(
            "gliner",
            required=True,
            available=False,
            message="missing",
            remediation="Install missing module 'gliner' in the project environment and rerun readiness.",
            backends=("transformer",),
        ),
    ]
    model_checks = [
        ModelCheckResult(
            "urchade/gliner_multi_pii-v1",
            required=True,
            available=False,
            message="model missing",
            remediation="Provision model assets for 'urchade/gliner_multi_pii-v1' before enabling this backend.",
            backends=("transformer",),
        ),
    ]

    monkeypatch.setattr("src.bootstrap.readiness_bootstrap.run_dependency_checks", lambda: dependency_checks)
    monkeypatch.setattr("src.bootstrap.readiness_bootstrap.run_model_checks", lambda: model_checks)

    descriptors = build_backend_descriptors()
    by_engine = {descriptor.engine_id: descriptor for descriptor in descriptors}

    assert by_engine["transformer"].availability_status == "unavailable"


def test_run_dependency_checks_includes_cpu_only_compatibility() -> None:
    from src.bootstrap.dependency_check import run_dependency_checks

    checks = run_dependency_checks()
    cpu_checks = [item for item in checks if item.name == "cpu_only_compatibility"]

    assert len(cpu_checks) == 1
    assert cpu_checks[0].required is True
    assert cpu_checks[0].available is True
