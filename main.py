"""
Two-stage job posting screenshot checker.

Stage 1 (gate):  Is this image actually a job posting?
Stage 2 (scam):  If yes, does it look legitimate or fake?

Setup:  python -m pip install -r requirements.txt
Usage:  python laya_jd_prob.py                 (uses IMAGE_FOLDER from .env)
        python laya_jd_prob.py <folder|image>  (override)

Do NOT name this file laya.py (it would shadow the library).
"""

import re
import sys
from pathlib import Path

import easyocr
import torch

from config import IMAGE_FOLDER
from laya import Router

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MIN_TEXT_CHARS = 30

FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com",
             "hotmail.com", "proton.me", "protonmail.com", "rediffmail.com"}

# ---------------------------------------------------------------- Stage 1 ---
JOB_KEYWORDS = [
    "hiring", "vacanc", "opening", "job", "position", "role", "apply",
    "resume", "cv", "experience", "responsibilit", "qualification",
    "requirement", "salary", "ctc", "skills", "recruit", "candidate",
    "joiner", "full-time", "full time", "part-time", "internship",
    "remote", "hybrid", "on-site", "onsite",
]
KEYWORD_PASS = 4  # this many distinct keywords passes even if the model disagrees

GATE_QUESTIONS = {
    "doc_type": {
        "type": "choice",
        "instructions": "What kind of content is this text?",
        "criteria": {
            "job_posting": "an employer or recruiter advertising an open position or vacancy",
            "job_seeker": "a person looking for work: a resume, CV, or 'open to work' post",
            "other": "anything else: memes, chats, ads, articles, app screenshots, random text",
        },
    },
}

# ---------------------------------------------------------------- Stage 2 ---
SCAM_QUESTIONS = {
    "verdict": {
        "type": "choice",
        "instructions": "Based on the wording and structure, is this job posting legitimate?",
        "criteria": {
            "legit": "a specific role with clear requirements; terse recruiter-style posts are normal",
            "suspicious": "several vague or exaggerated elements but not conclusive",
            "likely_scam": "classic fake-job patterns: upfront fees, unrealistic pay, chat-app contact",
        },
    },
    "scam_score": {
        "type": "score",
        "instructions": "How likely is this posting to be fraudulent?",
        "criteria": ["looks genuine", "some concerns", "highly likely fake"],
    },
    "upfront_payment": {
        "type": "noul",
        "instructions": "Does the posting ask the applicant to pay a fee, buy equipment, or send money?",
    },
    "unrealistic_pay": {
        "type": "noul",
        "instructions": "Is the pay unrealistically high for the stated skills, hours, or experience?",
    },
    "off_platform_contact": {
        "type": "noul",
        "instructions": "Does it ask applicants to contact via Telegram, WhatsApp, or a free personal "
                        "email (gmail, yahoo, outlook)? A company-domain email is normal.",
    },
    "vague_details": {
        "type": "noul",
        "instructions": "Are the role and responsibilities described in vague, generic terms?",
    },
    "urgency_pressure": {
        "type": "noul",
        "instructions": "Does it pressure the applicant with scarcity or deadlines (e.g. 'limited spots', "
                        "'act now')? Ignore standard hiring terms like 'immediate joiners' or notice period.",
    },
}

HARD_FLAGS = ["upfront_payment", "off_platform_contact"]
SOFT_FLAGS = ["unrealistic_pay", "vague_details", "urgency_pressure"]

_reader = None
_router = None


def get_router() -> Router:
    global _router
    if _router is None:
        _router = Router()
    return _router

# OCR fucn to extract text from image using easyocr
def extract_text(image_path: Path) -> str:
    """OCR one image and return its text."""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
    lines = _reader.readtext(str(image_path), detail=0, paragraph=True)
    return "\n".join(lines)

# Checks if email has a domain (Easy to spoof)
def email_domains(text: str) -> set[str]:
    return {d.lower() for d in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text)}

def keyword_hits(text: str) -> int:
    lower = text.lower()
    return sum(1 for k in JOB_KEYWORDS if re.search(r"\b" + re.escape(k), lower))

# For junk image filtering screenshots
def check_is_job_post(text: str) -> dict:
    """Stage 1: keyword check + model classification."""
    hits = keyword_hits(text)
    kind = get_router().predict(text, GATE_QUESTIONS)["answers"]["doc_type"]["choice"]
    is_job = kind == "job_posting" or hits >= KEYWORD_PASS
    return {"kind": kind, "hits": hits, "is_job": is_job}


def analyze_scam(text: str) -> dict:
    """Stage 2: red-flag analysis of a confirmed job posting."""
    answers = get_router().predict(text, SCAM_QUESTIONS)["answers"]

    domains = email_domains(text)
    uses_free_mail = bool(domains & FREE_MAIL)
    has_company_mail = bool(domains - FREE_MAIL)

    probs = {f: answers[f]["noul"] for f in HARD_FLAGS + SOFT_FLAGS}
    verdict = answers["verdict"]["choice"]

    # Code-level check beats model guesswork for email domains.
    if uses_free_mail:
        probs["off_platform_contact"] = max(probs["off_platform_contact"], 0.9)
    elif has_company_mail:
        probs["off_platform_contact"] = min(probs["off_platform_contact"], 0.3)

    hard_hit = any(probs[f] > 0.7 for f in HARD_FLAGS)
    soft_count = sum(probs[f] > 0.6 for f in SOFT_FLAGS)

    if hard_hit or verdict == "likely_scam":
        decision = "LIKELY FAKE - do not apply ❌"
    elif soft_count >= 2 or verdict == "suspicious":
        decision = "SUSPICIOUS - verify the company before applying ⚠️"
    else:
        decision = "Looks legitimate ✅"

    return {"verdict": verdict, "scam_score": answers["scam_score"],
            "probs": probs, "domains": domains, "decision": decision}


def find_images() -> list[Path]:
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


def process_image(path: Path) -> tuple[str, str]:
    """Run the full pipeline on one image. Returns (type, outcome) for the summary."""
    print(f"\n===== {path.name} =====")

    # OCR for text extraction
    text = extract_text(path)
    if len(text.strip()) < MIN_TEXT_CHARS:
        print("[skip] Very little text found. Use a sharper, higher-resolution screenshot.")
        return "no text", "skipped"

    print("--- Extracted text (check OCR quality) ---")
    print(text)
    print(f"--- End of text ({len(text)} chars) ---")

    # Stage 1: is it a job posting?
    gate = check_is_job_post(text)
    print(f"\n--- Stage 1: content check ---")
    print(f"Model says: {gate['kind']} | job keywords found: {gate['hits']}")
    if not gate["is_job"]:
        reason = {"job_seeker": "this looks like a resume / job-seeker post",
                  "other": "this does not look like a job posting"}.get(gate["kind"], "not a job posting")
        print(f">> Skipped: {reason}.")
        return gate["kind"], "skipped (not a job posting) ⏩"

    # Stage 2: is it legit?
    r = analyze_scam(text)
    print("\n--- Stage 2: scam analysis ---")
    print("Verdict:", r["verdict"])
    print("Scam score (raw):", r["scam_score"])
    print("Email domains:", ", ".join(sorted(r["domains"])) or "none found")
    for name, p in r["probs"].items():
        print(f"  {name}: {p:.0%}")
    print("\n>>", r["decision"])
    return "job_posting", r["decision"]


def main() -> None:
    images = find_images()
    print(f"Found {len(images)} image(s) to analyze.")

    summary = []
    for path in images:
        try:
            kind, outcome = process_image(path)
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