from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: int
    status: str
    message: str
