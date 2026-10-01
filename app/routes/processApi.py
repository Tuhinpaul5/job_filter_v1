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

# @router.post("/batch", response_model=list[ProcessResponse])
# async def process_batch(files: list[UploadFile] = File(...)):
#     if len(files) > MAX_BATCH_FILES:
#         raise HTTPException(400, f"Too many files (max {MAX_BATCH_FILES}).")

#     results = []
#     for file in files:
#         try:
#             results.append(await analyze_upload(file))
#         except Exception as exc:  # keep going if one image fails
#             results.append(error_response(file.filename or "unknown", exc))
#     return results


# @router.post("/text", response_model=ProcessResponse)
# async def process_text(body: TextRequest):
#     try:
#         return await run_in_threadpool(analyze_text, body.text, body.filename)
#     except Exception as exc:
#         raise HTTPException(500, f"Processing failed: {exc}")


# def _analyze_folder(images) -> list[ProcessResponse]:
#     results = []
#     for path in images:
#         try:
#             results.append(analyze_image(path, path.name))
#         except Exception as exc:  # keep going if one image fails
#             results.append(error_response(path.name, exc))
#     return results


# @router.get("/folder", response_model=list[ProcessResponse])
# async def process_folder():
#     if not IMAGE_FOLDER.is_dir():
#         raise HTTPException(404, f"Folder not found: {IMAGE_FOLDER}")
#     images = sorted(p for p in IMAGE_FOLDER.iterdir() if p.suffix.lower() in IMAGE_EXTS)
#     if not images:
#         raise HTTPException(404, f"No images found in: {IMAGE_FOLDER}")

#     return await run_in_threadpool(_analyze_folder, images)
