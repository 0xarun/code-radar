import asyncio
import logging
import shutil
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.services.cache_service import CacheService
from app.services.ollama_service import OllamaService
from app.services.semgrep_service import SemgrepService
from app.utils.archive import safe_extract_zip
from app.utils.hashing import sha256_text
from app.utils.semgrep_parser import parse_semgrep_findings

logger = logging.getLogger(__name__)


class ScanPipeline:
    def __init__(self) -> None:
        self.semgrep = SemgrepService()
        self.cache = CacheService()
        self.ollama = OllamaService()

    async def execute(self, session: AsyncSession, job_id: int, zip_path: Path, extract_path: Path, max_concurrency: int) -> tuple[int, int, float]:
        started = time.perf_counter()
        safe_extract_zip(zip_path, extract_path)
        semgrep_raw = self.semgrep.run_scan(extract_path)
        findings_raw = parse_semgrep_findings(semgrep_raw)

        semaphore = asyncio.Semaphore(max_concurrency)
        cached_hits = 0
        llm_times: list[float] = []
        db_rows: list[Finding] = []

        async def enrich(finding: dict[str, str]) -> None:
            nonlocal cached_hits
            hash_input = f"{finding['file_path']}|{finding['rule_id']}|{finding['code_snippet']}"
            finding_hash = sha256_text(hash_input)
            cached = await self.cache.get(finding_hash)
            if cached:
                cached_hits += 1
                analysis = cached
                llm_time = 0.0
            else:
                async with semaphore:
                    analysis, llm_time = await self.ollama.analyze(finding)
                    await self.cache.set(finding_hash, analysis)
            llm_times.append(llm_time)
            db_rows.append(
                Finding(
                    job_id=job_id,
                    file_path=finding["file_path"],
                    rule_id=finding["rule_id"],
                    severity=finding["severity"],
                    code_snippet=finding["code_snippet"],
                    hash=finding_hash,
                    ai_analysis=analysis,
                )
            )

        await asyncio.gather(*(enrich(f) for f in findings_raw))

        session.add_all(db_rows)
        await session.commit()

        duration = time.perf_counter() - started
        logger.info("Job completed", extra={"event": "job.done", "job_id": job_id, "duration": duration})
        shutil.rmtree(extract_path, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        return len(db_rows), cached_hits, duration
