import React, { useState } from "react";
import axios from "axios";

type MatchResult = {
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  recommendations: string[];
  rewritten_bullets: string[];
  verification_notes: string[];
};

const API_BASE_URL = "http://localhost:8000";

export const App: React.FC = () => {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post<MatchResult>(`${API_BASE_URL}/api/analyze`, {
        resume_text: resumeText,
        job_description: jobDescription,
      });
      setResult(response.data);
    } catch (err) {
      setError("Something went wrong while analyzing. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResumeText("");
    setJobDescription("");
    setResult(null);
    setError(null);
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1>AI Resume & Job Matching Agent Platform</h1>
          <p className="subtitle">Multi-Agent Resume Optimization &amp; Job Matching System</p>
        </div>
        <div className="badge">Best for career + GPA</div>
      </header>

      <main className="layout">
        <section className="panel input-panel">
          <h2>1. Upload / Paste Your Resume & Job Description</h2>
          <p className="panel-subtitle">
            Paste raw text for now. We&apos;ll add PDF parsing on top of this API later.
          </p>

          <div className="field-group">
            <label>Resume Text</label>
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste your resume here..."
              rows={10}
            />
          </div>

          <div className="field-group">
            <label>Job Description</label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the target job description here..."
              rows={8}
            />
          </div>

          <div className="actions">
            <button onClick={handleAnalyze} disabled={loading || !resumeText || !jobDescription}>
              {loading ? "Analyzing..." : "Run Multi-Agent Analysis"}
            </button>
            <button className="ghost" onClick={handleReset}>
              Reset
            </button>
          </div>

          {error && <p className="error-text">{error}</p>}
        </section>

        <section className="panel results-panel">
          <h2>2. Agent Insights</h2>
          {!result && <p className="placeholder">Run the analysis to see ATS score and suggestions.</p>}

          {result && (
            <div className="results-grid">
              <div className="card score-card">
                <h3>ATS Match Score</h3>
                <div className="score-circle">
                  <span>{result.score}</span>
                  <span className="score-unit">/ 100</span>
                </div>
                <p className="score-caption">
                  Higher scores mean your resume is more aligned with the job description keywords and skills.
                </p>
              </div>

              <div className="card">
                <h3>Parser & Matching Agents</h3>
                <div className="tags-block">
                  <h4>Matched Skills</h4>
                  <div className="tags">
                    {result.matched_skills.length === 0 && <span className="tag muted">No strong matches detected yet</span>}
                    {result.matched_skills.map((skill) => (
                      <span key={skill} className="tag success">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="tags-block">
                  <h4>Missing / Weak Skills</h4>
                  <div className="tags">
                    {result.missing_skills.length === 0 && <span className="tag muted">No obvious gaps detected</span>}
                    {result.missing_skills.map((skill) => (
                      <span key={skill} className="tag warning">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card">
                <h3>Resume Rewrite Agent</h3>
                <ul className="list">
                  {result.rewritten_bullets.map((bullet, idx) => (
                    <li key={idx}>{bullet}</li>
                  ))}
                </ul>
              </div>

              <div className="card">
                <h3>Gap Analysis Agent</h3>
                <ul className="list">
                  {result.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>

              <div className="card">
                <h3>Verification Agent</h3>
                <ul className="list">
                  {result.verification_notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

