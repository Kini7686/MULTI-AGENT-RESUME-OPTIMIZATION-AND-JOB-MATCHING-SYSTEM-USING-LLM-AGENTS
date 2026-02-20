## Multi-Agent Resume Optimization & Job Matching System

This project is an AI-powered web application that helps candidates optimize their resumes for specific job descriptions using **multi-agent LLM workflows**.

### High-Level Flow

- User uploads:
  - Resume (PDF / text)
  - Job description (text / PDF)
- Backend runs a coordinated set of LLM agents:
  - Parser Agent → extracts skills, experience, and entities
  - Matching Agent → computes ATS-style relevance score and highlights matches/gaps
  - Resume Rewrite Agent → suggests improved bullet points and summary
  - Gap Analysis Agent → recommends courses / projects / learning plan
  - Verification Agent → checks for hallucinations and flags risky edits
- Frontend displays:
  - Overall match score and explanation
  - Suggested improved resume sections
  - Skills gap analysis and learning plan
  - Verification notes for human-in-the-loop review

### Tech Stack

- **Frontend**: React (Vite) + TypeScript
- **Backend**: FastAPI (Python)
- **Agents**: LangChain-style tools + simple Crew-style coordination (non-vendor locked, vanilla Python abstractions)
- **Vector Store**: Pluggable interface (in-memory FAISS-like index to start)

### Project Structure

- `backend/` – FastAPI app and agent logic
- `frontend/` – React app (Vite + TS)

You can run backend and frontend separately during development, then deploy them together behind a reverse proxy or on a PaaS.

