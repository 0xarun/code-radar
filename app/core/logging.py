import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for machine-readable structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for attr in ("job_id", "event", "duration", "status"):
            if hasattr(record, attr):
                payload[attr] = getattr(record, attr)
        return json.dumps(payload)


def setup_logging(log_file: Path, level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    file_handler.setFormatter(JsonFormatter())

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())

    root.addHandler(file_handler)
    root.addHandler(stream_handler)
