import json
import logging
import subprocess
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SemgrepService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def run_scan(self, target_dir: Path) -> dict:
        cmd = [
            self.settings.semgrep_bin,
            "scan",
            "--config",
            self.settings.semgrep_config,
            "--json",
            str(target_dir),
        ]
        logger.info("Starting semgrep scan", extra={"event": "semgrep.start"})
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode not in {0, 1}:
            logger.error("Semgrep failed", extra={"event": "semgrep.error", "status": result.returncode})
            raise RuntimeError(f"Semgrep error: {result.stderr}")
        logger.info("Semgrep completed", extra={"event": "semgrep.end"})
        return json.loads(result.stdout or "{}")
