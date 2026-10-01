import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.process.context import IMAGE_EXTS, MIN_TEXT_CHARS
from app.process.process import Process

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Created once so the OCR reader and laya model load only once
process = Process()


def warm_up() -> None:
    """Load the laya model and OCR reader before the first request."""
    process.get_router()
    process.ocr.load()


class ProcessResponse(BaseModel):
    filename: str
    status: str                     # "analyzed" | "skipped" | "error"
    kind: str | None = None         # job_posting | job_seeker | other | no_text
    reason: str | None = None
    keyword_hits: int | None = None
    text: str | None = None
    verdict: str | None = None
    scam_score: Any = None
    probs: dict[str, float] | None = None
    domains: list[str] = []
    decision: str | None = None


def analyze_text(text: str, filename: str) -> ProcessResponse:
    """Run stage 1 + stage 2 on already-extracted text."""
    if len(text.strip()) < MIN_TEXT_CHARS:
        return ProcessResponse(filename=filename, status="skipped", kind="no_text",
                               reason="Very little text found. Upload a sharper screenshot.")

    # Stage 1: is it a job posting?
    gate = process.check_is_job_post(text)
    if not gate["is_job"]:
        reason = {"job_seeker": "This looks like a resume / job-seeker post.",
                  "other": "This does not look like a job posting."}.get(gate["kind"], "Not a job posting.")
        return ProcessResponse(filename=filename, status="skipped", kind=gate["kind"],
                               reason=reason, keyword_hits=gate["hits"], text=text)

    # Stage 2: is it legit?
    r = process.analyze_scam(text)
    return ProcessResponse(
        filename=filename, status="analyzed", kind="job_posting",
        keyword_hits=gate["hits"], text=text,
        verdict=r["verdict"], scam_score=r["scam_score"],
        probs={k: float(v) for k, v in r["probs"].items()},
        domains=sorted(r["domains"]), decision=r["decision"],
    )


def analyze_image(path: Path, filename: str) -> ProcessResponse:
    return analyze_text(process.ocr.extract_text(path), filename)


def _analyze_bytes(data: bytes, suffix: str, filename: str) -> ProcessResponse:
    """Blocking part: save to a temp file, OCR it, run the model."""
    # Ocr.extract_text takes a path, so save the upload to a temp file.
    # Close it before OCR: Windows won't let another reader open it otherwise.
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        return analyze_image(Path(tmp.name), filename)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


async def analyze_upload(file: UploadFile) -> ProcessResponse:
    """Validate an upload, then analyze it in a worker thread."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in IMAGE_EXTS:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Allowed: {sorted(IMAGE_EXTS)}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")

    return await run_in_threadpool(_analyze_bytes, data, suffix, file.filename)


def error_response(filename: str, exc: Exception) -> ProcessResponse:
    reason = exc.detail if isinstance(exc, HTTPException) else f"Processing failed: {exc}"
    return ProcessResponse(filename=filename, status="error", reason=reason)
