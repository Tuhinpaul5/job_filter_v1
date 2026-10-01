
import re

from app.process.context import JOB_KEYWORDS

class ImageProcessor:
    def __init__(self):
        pass

    # Checks if email has a domain (Easy to spoof)
    def email_domains(self, text: str) -> set[str]:
        return {d.lower() for d in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text)}

    def keyword_hits(self, text: str) -> int:
        lower = text.lower()
        return sum(1 for k in JOB_KEYWORDS if re.search(r"\b" + re.escape(k), lower))
