from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import LOGS_DIR


def configure_logging(level: int = logging.INFO) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "anonymapp.log"
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return log_path

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    stream_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    return log_path


def translate_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "Input file not found. Verify the provided path."
    if isinstance(exc, PermissionError):
        return "Access denied for file operation. Check file and directory permissions."
    if isinstance(exc, ModuleNotFoundError):
        return "Missing runtime dependency. Run readiness checks and install required packages."
    if isinstance(exc, ValueError):
        return f"Invalid input: {exc}"
    name = exc.__class__.__name__
    return f"{name}: {exc}"


def log_and_translate_error(logger: logging.Logger, exc: Exception, context: str) -> str:
    logger.exception("%s failed: %s", context, exc)
    return translate_error(exc)
