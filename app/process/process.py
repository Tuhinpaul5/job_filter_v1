"""
Two-stage job posting screenshot checker.

Stage 1 (gate):  Is this image actually a job posting?
Stage 2 (scam):  If yes, does it look legitimate or fake?

Setup:  python -m pip install -r requirements.txt
Usage:  python laya_jd_prob.py                 (uses IMAGE_FOLDER from .env)
        python laya_jd_prob.py <folder|image>  (override)

Do NOT name this file laya.py (it would shadow the library).
"""
from pathlib import Path

from app.helpers.ocr import Ocr
from app.process.image_processor import ImageProcessor
from app.process.context import FREE_MAIL, GATE_QUESTIONS, IMAGE_EXTS, KEYWORD_PASS, MIN_TEXT_CHARS, SCAM_QUESTIONS

from config import IMAGE_FOLDER
from laya import Router

import tempfile


class Process:
    def __init__(self):
        self.HARD_FLAGS = ["upfront_payment", "off_platform_contact"]
        self.SOFT_FLAGS = ["unrealistic_pay", "vague_details", "urgency_pressure"]

        self._reader = None
        self._router = None

        self.ocr = Ocr()
        self.image_processor = ImageProcessor()

    @staticmethod
    def _jsonable(obj):
        """Make sets / numpy types JSON serializable."""
        if isinstance(obj, dict):
            return {str(k): Process._jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set, frozenset)):
            items = sorted(obj) if isinstance(obj, (set, frozenset)) else obj
            return [Process._jsonable(v) for v in items]
        if hasattr(obj, "item"):  # numpy scalar
            return obj.item()
        return obj

    def get_router(self) -> Router:
        if self._router is None:
            self._router = Router()
        return self._router

    # For junk image filtering screenshots
    def check_is_job_post(self, text: str) -> dict:
        """Stage 1: keyword check + model classification."""
        hits = self.image_processor.keyword_hits(text)
        kind = self.get_router().predict(text, GATE_QUESTIONS)["answers"]["doc_type"]["choice"]
        is_job = kind == "job_posting" or hits >= KEYWORD_PASS
        return {"kind": kind, "hits": hits, "is_job": is_job}

    def analyze_scam(self,text: str) -> dict:
        """Stage 2: red-flag analysis of a confirmed job posting."""
        answers = self.get_router().predict(text, SCAM_QUESTIONS)["answers"]

        domains = self.image_processor.email_domains(text)
        uses_free_mail = bool(domains & FREE_MAIL)
        has_company_mail = bool(domains - FREE_MAIL)

        probs = {f: answers[f]["noul"] for f in self.HARD_FLAGS + self.SOFT_FLAGS}
        verdict = answers["verdict"]["choice"]

        # Code-level check beats model guesswork for email domains.
        if uses_free_mail:
            probs["off_platform_contact"] = max(probs["off_platform_contact"], 0.9)
        elif has_company_mail:
            probs["off_platform_contact"] = min(probs["off_platform_contact"], 0.3)

        hard_hit = any(probs[f] > 0.7 for f in self.HARD_FLAGS)
        soft_count = sum(probs[f] > 0.6 for f in self.SOFT_FLAGS)

        if hard_hit or verdict == "likely_scam":
            decision = "LIKELY FAKE - do not apply ❌"
        elif soft_count >= 2 or verdict == "suspicious":
            decision = "SUSPICIOUS - verify the company before applying ⚠️"
        else:
            decision = "Looks legitimate ✅"

        return {"verdict": verdict, "scam_score": answers["scam_score"],
                "probs": probs, "domains": domains, "decision": decision}


    def _analyze_path(self, path: Path) -> dict:
        """Run the pipeline on one image and return a structured verdict."""
        text = self.ocr.extract_text(path)
        if len(text.strip()) < MIN_TEXT_CHARS:
            return {"verdict": "skipped",
                    "reason": "Very little text found. Use a sharper, higher-resolution screenshot."}

        gate = self.check_is_job_post(text)
        if not gate["is_job"]:
            reason = {"job_seeker": "this looks like a resume / job-seeker post",
                      "other": "this does not look like a job posting"
                      }.get(gate["kind"], "not a job posting")
            return {"verdict": "skipped", "reason": reason,
                    "doc_type": gate["kind"], "keyword_hits": gate["hits"]}

        r = self.analyze_scam(text)
        return {
            "verdict": r["verdict"],                      # e.g. "legit"
            "decision": r["decision"],
            "scam_score": r["scam_score"],                # raw model output
            "email_domains": r["domains"] or [],          # [] if none found
            "flags": {name: round(p, 4) for name, p in r["probs"].items()},
        }

    def process_job(self, images: list) -> dict:
        """
        images: list of file paths (str/Path) OR upload objects exposing
                `.filename` and `.file` (FastAPI UploadFile / Flask FileStorage-like).
        """
        try:
            data = []
            with tempfile.TemporaryDirectory() as tmp:
                for i, img in enumerate(images):
                    try:
                        if isinstance(img, (str, Path)):
                            path, name = Path(img), Path(img).name
                        else:
                            name = getattr(img, "filename", None) or f"image_{i}.jpg"
                            path = Path(tmp) / f"{i}_{Path(name).name}"
                            stream = getattr(img, "file", img)
                            path.write_bytes(stream.read())

                        verdict = self._analyze_path(path)
                    except Exception as exc:  # keep going if one image fails
                        verdict = {"verdict": "error", "reason": str(exc)}
                    data.append({"file_name": name if 'name' in locals() else f"image_{i}",
                                "file_verdict": self._jsonable(verdict)})

            return {"status": True, "message": "Successfully processed", "data": data}
        except Exception as exc:
            return {"status": False, "message": f"Processing failed: {exc}", "data": []}