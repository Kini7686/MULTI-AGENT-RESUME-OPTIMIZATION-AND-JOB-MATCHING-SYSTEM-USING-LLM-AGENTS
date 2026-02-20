from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional


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
    Placeholder implementation of the multi-agent pipeline.
    This will be replaced with real LLM + vector search agents.
    """
    # Very naive heuristic for now
    base_skills = ["Python", "Machine Learning", "FastAPI", "React", "SQL", "LangChain"]
    matched = [s for s in base_skills if s.lower() in request.resume_text.lower()]
    missing = [s for s in base_skills if s not in matched]

    score = len(matched) / len(base_skills) if base_skills else 0.0

    return MatchResult(
        score=round(score * 100, 1),
        matched_skills=matched,
        missing_skills=missing,
        recommendations=[f"Strengthen your knowledge of {s}" for s in missing],
        rewritten_bullets=[
            "Optimized sample bullet: Delivered end-to-end AI features using FastAPI and React.",
            "Optimized sample bullet: Improved ATS score by aligning resume keywords with job description.",
        ],
        verification_notes=[
            "Verify that all claimed projects and metrics are factually correct.",
            "Do not add tools or skills you have never used in practice.",
        ],
    )


@app.post("/api/analyze-upload", response_model=MatchResult)
async def analyze_resume_upload(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """
    Endpoint that will parse PDF/Docx uploads.
    Currently, it simply reads text content from the uploaded file as UTF-8.
    """
    content_bytes = await resume_file.read()
    try:
        resume_text = content_bytes.decode("utf-8", errors="ignore")
    except Exception:
        resume_text = ""

    return await analyze_resume(AnalyzeRequest(resume_text=resume_text, job_description=job_description))


