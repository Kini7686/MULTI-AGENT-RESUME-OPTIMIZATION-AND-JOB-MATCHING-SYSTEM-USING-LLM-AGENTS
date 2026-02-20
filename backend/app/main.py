import json
import os
import re
from collections import Counter
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pypdf import PdfReader


class MatchResult(BaseModel):
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    recommendations: List[str]
    rewritten_bullets: List[str]
    verification_notes: List[str]


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "are",
    "was",
    "were",
    "from",
    "have",
    "has",
    "had",
    "you",
    "your",
    "their",
    "our",
    "about",
    "into",
    "over",
    "such",
    "using",
    "based",
    "skills",
    "experience",
    "job",
    "role",
    "responsibilities",
}


def extract_keywords(text: str, max_keywords: int = 40) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#\-.]*", text.lower())
    counts: Counter[str] = Counter(
        w for w in words if len(w) > 2 and w not in STOP_WORDS
    )
    return [w for w, _ in counts.most_common(max_keywords)]


def extract_bullet_points(text: str) -> List[str]:
    """Extract bullet points from resume text."""
    bullets = []
    # Look for lines starting with bullet markers or dashes
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped.startswith("•") or stripped.startswith("-") or stripped.startswith("*")):
            bullet = stripped.lstrip("•-*").strip()
            if len(bullet) > 10:  # Only meaningful bullets
                bullets.append(bullet)
        elif stripped and len(stripped) > 20 and not stripped[0].isupper() and not stripped.startswith(" "):
            # Also catch lines that look like bullets (short, action-oriented)
            if any(stripped.lower().startswith(verb) for verb in ["developed", "created", "implemented", "designed", "built", "managed", "led", "improved", "optimized"]):
                bullets.append(stripped)
    return bullets[:15]  # Limit to first 15 bullets


def heuristic_analysis(request: AnalyzeRequest) -> MatchResult:
    jd_keywords = extract_keywords(request.job_description)
    resume_keywords = set(extract_keywords(request.resume_text, max_keywords=120))

    matched = [k for k in jd_keywords if k in resume_keywords]
    missing = [k for k in jd_keywords if k not in resume_keywords]

    coverage = len(matched) / max(len(jd_keywords), 1)
    score = round(coverage * 100, 1)

    # Extract actual bullets from resume
    resume_bullets = extract_bullet_points(request.resume_text)
    
    # Generate before/after suggestions
    recommendations = []
    if resume_bullets:
        for bullet in resume_bullets[:5]:  # Take first 5 bullets
            # Find missing keywords that could enhance this bullet
            bullet_lower = bullet.lower()
            relevant_missing = [kw for kw in missing[:3] if kw not in bullet_lower]
            if relevant_missing:
                kw = relevant_missing[0]
                # Create a before/after suggestion
                recommendations.append(
                    f"Instead of: \"{bullet[:80]}{'...' if len(bullet) > 80 else ''}\"\n"
                    f"Use: \"{bullet[:60]} using {kw.title()} with measurable impact\""
                )
    
    if not recommendations:
        # Fallback if no bullets found
        recommendations = [
            f"Instead of: \"Developed application\"\n"
            f"Use: \"Developed MERN stack application with AWS integration, improving performance by 30%\""
        ]

    # Generate example optimized bullets based on missing keywords
    rewritten_bullets = []
    if missing:
        top_missing = missing[:3]
        for kw in top_missing:
            rewritten_bullets.append(
                f"Example optimized bullet: Developed {kw} solution that improved [metric] by [X]%, "
                f"demonstrating expertise in {kw} and alignment with job requirements."
            )
    if not rewritten_bullets:
        rewritten_bullets = [
            "Add quantified achievements (e.g., 'Improved performance by 30%', 'Reduced costs by $50K').",
            "Include specific technologies from the job description that you've actually used.",
        ]

    # Generate specific verification notes based on resume content
    verification_notes = []
    resume_lower = request.resume_text.lower()
    jd_lower = request.job_description.lower()
    
    # Check for potential copied language
    common_phrases = ["responsible for", "duties include", "required skills"]
    copied_count = sum(1 for phrase in common_phrases if phrase in resume_lower and phrase in jd_lower)
    if copied_count > 2:
        verification_notes.append(
            "Warning: Your resume contains phrases that appear copied directly from the job description. "
            "Rewrite these sections in your own words while keeping the same meaning."
        )
    
    # Check for missing metrics
    has_numbers = bool(re.search(r'\d+%|\$\d+|\d+\s*(users|clients|customers|projects)', resume_lower))
    if not has_numbers:
        verification_notes.append(
            "Your resume lacks quantifiable metrics (percentages, dollar amounts, user counts). "
            "Add specific numbers to demonstrate impact (e.g., 'increased revenue by 25%', 'served 10K users')."
        )
    
    # Check for vague claims
    vague_words = ["some", "various", "several", "many", "extensive"]
    vague_count = sum(1 for word in vague_words if word in resume_lower)
    if vague_count > 3:
        verification_notes.append(
            "Replace vague terms like 'some', 'various', 'several' with specific numbers or concrete examples."
        )
    
    if not verification_notes:
        verification_notes = [
            "Review all technical skills listed to ensure you can discuss them confidently in an interview.",
            "Verify that all dates, company names, and project details are accurate.",
        ]

    return MatchResult(
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        recommendations=recommendations,
        rewritten_bullets=rewritten_bullets,
        verification_notes=verification_notes,
    )


def ai_analysis(request: AnalyzeRequest) -> MatchResult:
    """
    AI-powered deep analysis using OpenAI (via langchain-openai).
    Falls back to heuristic logic if anything goes wrong.
    """
    if not OPENAI_API_KEY:
        return heuristic_analysis(request)

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        prompt = """
You are an ATS-style resume screening assistant.
Compare the candidate's RESUME to the JOB DESCRIPTION.
Return a STRICT JSON object with these keys:
- score: number from 0 to 100 (float)
- matched_keywords: list of important skills/keywords that appear in BOTH resume and JD
- missing_keywords: list of important skills/keywords that are in the JD but NOT clearly present in the resume
- optimal_points: list of BEFORE/AFTER bullet point replacements. Each item must be a string with this EXACT format:
  "Instead of: [existing bullet point from resume]\nUse: [optimized bullet point with JD keywords and impact]"
  Example:
  "Instead of: Developed application\nUse: Developed MERN stack application with AWS integration, reducing load time by 40%"
  Extract actual bullet points from the resume and suggest concrete replacements that include missing JD keywords and quantifiable impact.
- rewritten_bullets: 2-4 CONCRETE example bullet points that the candidate could add to their resume.
  These should be NEW bullets (not replacements) that incorporate missing JD keywords and include quantifiable metrics.
  Format each as a complete bullet point sentence, e.g., "Developed MERN stack application with AWS integration, serving 10K+ users and reducing latency by 40%"
- verification_notes: 2-4 SPECIFIC warnings about the actual resume content. Check for:
  * Phrases copied directly from the JD (flag exact matches)
  * Missing quantifiable metrics (percentages, dollar amounts, user counts)
  * Vague claims that need specificity
  * Technologies mentioned without context
  Format as actionable warnings, e.g., "Your resume mentions 'Python' but lacks specific projects using it. Add a bullet showing Python in action."

Do not include any text outside the JSON. No explanations.
"""
        user_block = f"JOB DESCRIPTION:\n{request.job_description}\n\nRESUME:\n{request.resume_text}"

        response = llm.invoke(prompt + "\n\n" + user_block)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(content)

        score_raw = float(data.get("score", 0.0))
        score = round(max(0.0, min(100.0, score_raw)), 1)

        return MatchResult(
            score=score,
            matched_skills=[str(x) for x in data.get("matched_keywords", [])],
            missing_skills=[str(x) for x in data.get("missing_keywords", [])],
            recommendations=[str(x) for x in data.get("optimal_points", [])],
            rewritten_bullets=[str(x) for x in data.get("rewritten_bullets", [])],
            verification_notes=[str(x) for x in data.get("verification_notes", [])],
        )
    except Exception:
        return heuristic_analysis(request)


app = FastAPI(title="Multi-Agent Resume Optimization & Job Matching API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=MatchResult)
async def analyze_resume(request: AnalyzeRequest):
    """
    Deep analysis of resume vs job description.
    Uses OpenAI when configured, otherwise a strong keyword-based heuristic.
    """
    return ai_analysis(request)


@app.post("/api/analyze-upload", response_model=MatchResult)
async def analyze_resume_upload(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """
    Analyze an uploaded resume file plus job description text.
    Supports PDF (preferred) and falls back to UTF-8 text decoding.
    """
    content_bytes = await resume_file.read()
    resume_text = ""

    if resume_file.content_type == "application/pdf" or resume_file.filename.lower().endswith(
        ".pdf"
    ):
        try:
            reader = PdfReader(BytesIO(content_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            resume_text = "\n".join(pages_text)
        except Exception:
            resume_text = ""

    if not resume_text:
        # Fallback: try to interpret as UTF-8 text
        try:
            resume_text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            resume_text = ""

    request = AnalyzeRequest(resume_text=resume_text, job_description=job_description)
    return ai_analysis(request)


