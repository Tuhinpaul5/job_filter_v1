"""
Two-stage job posting screenshot checker.

Stage 1 (gate):  Is this image actually a job posting?
Stage 2 (scam):  If yes, does it look legitimate or fake?

Setup:  python -m pip install -r requirements.txt
Usage:  python laya_jd_prob.py                 (uses IMAGE_FOLDER from .env)
        python laya_jd_prob.py <folder|image>  (override)

Do NOT name this file laya.py (it would shadow the library).
"""

import sys
from pathlib import Path

from app.helpers.ocr import Ocr
from image_processor import ImageProcessor

from config import IMAGE_FOLDER
from laya import Router

from context import FREE_MAIL, GATE_QUESTIONS, IMAGE_EXTS, KEYWORD_PASS, MIN_TEXT_CHARS, SCAM_QUESTIONS


class Process:
    def __init__(self):
        self.HARD_FLAGS = ["upfront_payment", "off_platform_contact"]
        self.SOFT_FLAGS = ["unrealistic_pay", "vague_details", "urgency_pressure"]

        self._reader = None
        self. _router = None

        self.ocr = Ocr()
        self.image_processor = ImageProcessor()

    def get_router(self) -> Router:
        global _router
        if _router is None:
            _router = Router()
        return _router

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

    def find_images(self) -> list[Path]:
        """Use the folder/file from the command line if given, else IMAGE_FOLDER."""
        target = Path(sys.argv[1]) if len(sys.argv) > 1 else IMAGE_FOLDER
        if target.is_file():
            return [target]
        if not target.is_dir():
            sys.exit(f"Folder not found: {target}")
        images = sorted(p for p in target.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if not images:
            sys.exit(f"No images ({', '.join(sorted(IMAGE_EXTS))}) found in: {target}")
        return images

    def process_image(self, path: Path) -> tuple[str, str]:
        """Run the full pipeline on one image. Returns (type, outcome) for the summary."""
        print(f"\n===== {path.name} =====")

        # OCR for text extraction
        text = self.ocr.extract_text(path)
        if len(text.strip()) < MIN_TEXT_CHARS:
            print("[skip] Very little text found. Use a sharper, higher-resolution screenshot.")
            return "no text", "skipped"

        print("--- Extracted text (check OCR quality) ---")
        print(text)
        print(f"--- End of text ({len(text)} chars) ---")

        # Stage 1: is it a job posting?
        gate = self.check_is_job_post(text)
        print(f"\n--- Stage 1: content check ---")
        print(f"Model says: {gate['kind']} | job keywords found: {gate['hits']}")
        if not gate["is_job"]:
            reason = {"job_seeker": "this looks like a resume / job-seeker post",
                    "other": "this does not look like a job posting"}.get(gate["kind"], "not a job posting")
            print(f">> Skipped: {reason}.")
            return gate["kind"], "skipped (not a job posting) ⏩"

        # Stage 2: is it legit?
        r = self.analyze_scam(text)
        print("\n--- Stage 2: scam analysis ---")
        print("Verdict:", r["verdict"])
        print("Scam score (raw):", r["scam_score"])
        print("Email domains:", ", ".join(sorted(r["domains"])) or "none found")
        for name, p in r["probs"].items():
            print(f"  {name}: {p:.0%}")
        print("\n>>", r["decision"])
        return "job_posting", r["decision"]

    def main(self) -> None:
        images = self.find_images()
        print(f"Found {len(images)} image(s) to analyze.")

        summary = []
        for path in images:
            try:
                kind, outcome = self.process_image(path)
            except Exception as exc:  # keep going if one image fails
                print(f"[error] {path.name}: {exc}")
                kind, outcome = "error", str(exc)
            summary.append((path.name, kind, outcome))

        print("\n\n===== SUMMARY =====")
        width = max(len(n) for n, _, _ in summary)
        for name, kind, outcome in summary:
            print(f"{name:<{width}}  {kind:<12}  {outcome}")


    if __name__ == "__main__":
        main()