from pydantic import BaseModel


class HealthStatus(BaseModel):
    db: str
    redis: str
    ollama: str
    semgrep: str
