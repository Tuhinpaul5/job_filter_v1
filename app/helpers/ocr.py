from pathlib import Path

import easyocr
import torch


class Ocr:
    def __init__(self):
        self._reader = None

    def load(self) -> None:
        """Load the EasyOCR reader (slow; done once at startup)."""
        if self._reader is None:
            self._reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())

    def extract_text(self, image_path: Path) -> str:
        """OCR one image and return its text."""
        self.load()
        lines = self._reader.readtext(str(image_path), detail=0, paragraph=True)
        return "\n".join(lines)