import os
from pathlib import Path

from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


def _resolve(value: str) -> Path:
    """Turn a relative or absolute path string into an absolute Path."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


IMAGE_FOLDER = _resolve(os.getenv("IMAGE_FOLDER", "job_images"))