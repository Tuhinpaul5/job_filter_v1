from pathlib import Path

import easyocr
import torch


class Ocr:
    def __init__(self):
        pass

    def extract_text(self, image_path: Path) -> str:
            """OCR one image and return its text."""
            global _reader
            if _reader is None:
                _reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
            lines = _reader.readtext(str(image_path), detail=0, paragraph=True)
            return "\n".join(lines)