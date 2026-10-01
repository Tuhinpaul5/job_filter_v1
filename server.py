from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.helpers.analyzer import warm_up
from app.routes.processApi import router as process_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: load the models so the first request isn't slow
    await run_in_threadpool(warm_up)
    yield
    # Code after `yield` runs at shutdown (nothing to clean up yet)


app = FastAPI(title="Job Posting Checker", version="0.1.0", lifespan=lifespan)
app.include_router(process_router)


FRONTEND = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def frontend():
    return FileResponse(FRONTEND)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000)
