
import re

from context import FREE_MAIL, GATE_QUESTIONS, IMAGE_EXTS, JOB_KEYWORDS, KEYWORD_PASS, MIN_TEXT_CHARS, SCAM_QUESTIONS

class ImageProcessor:
    def __init__(self):
        pass

    # Checks if email has a domain (Easy to spoof)
    def email_domains(self, text: str) -> set[str]:
        return {d.lower() for d in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text)}

    def keyword_hits(self, text: str) -> int:
        lower = text.lower()
        return sum(1 for k in JOB_KEYWORDS if re.search(r"\b" + re.escape(k), lower))
