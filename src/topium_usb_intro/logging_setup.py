"""Local rotating logs, with no personal drive identifiers in normal log lines."""
from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from .profiles import config_path


def setup_logging() -> None:
    folder = config_path().parent
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "app.log", maxBytes=300_000, backupCount=2,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
