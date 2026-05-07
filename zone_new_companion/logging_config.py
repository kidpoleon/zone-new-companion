"""Application logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: Path) -> None:
    """Configure root logging handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "zone-new-companion.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
