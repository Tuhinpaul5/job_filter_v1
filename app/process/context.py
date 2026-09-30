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
