from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.helpers.analyzer import ProcessResponse
from app.process.process import Process
router = APIRouter(prefix="/process", tags=["process"])

process = Process()

MAX_BATCH_FILES = 20


class TextRequest(BaseModel):
    text: str
    filename: str = "text-input"


# Endpoints are async; the slow OCR/model work runs in a worker thread via run_in_threadpool

@router.post("/image")
async def process_image(file: UploadFile = File(...)):
    return process.process_job([file])

