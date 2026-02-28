import asyncio
import logging
import time

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def analyze(self, finding: dict[str, str]) -> tuple[str, float]:
        prompt = (
            "You are a security code reviewer. Explain this vulnerability, suggest a fix, "
            "and rate severity. Keep response <=200 words.\n"
            f"File: {finding['file_path']}\nRule: {finding['rule_id']}\n"
            f"Severity: {finding['severity']}\nSnippet:\n{finding['code_snippet']}"
        )
        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": False}
        url = f"{self.settings.ollama_url}/api/generate"
        last_error: Exception | None = None
        for attempt in range(1, self.settings.ollama_retries + 1):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    duration = time.perf_counter() - started
                    logger.info("Ollama call succeeded", extra={"event": "ollama.ok", "duration": duration})
                    return response.json().get("response", "No response."), duration
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning("Ollama call failed", extra={"event": "ollama.retry", "status": attempt})
                await asyncio.sleep(0.5 * attempt)
        raise RuntimeError(f"Ollama call failed after retries: {last_error}")
