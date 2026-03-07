from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import LOGS_DIR


def configure_logging(level: int = logging.INFO) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "anonymapp.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def translate_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    return f"{name}: {exc}"
