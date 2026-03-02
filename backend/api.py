import os
import io
import json
import re
import math
import logging
from collections import Counter
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _load_key(env_var: str) -> str:
    key = os.getenv(env_var)
    if not key:
        raise RuntimeError(f"{env_var} not found in .env file.")
    return key

GEMINI_MODEL = "gemini-2.5-flash"
EMBED_MODEL  = "gemini-embedding-001"

chat_client      = genai.Client(api_key=_load_key("CHATBOT_API_KEY"))
market_client    = genai.Client(api_key=_load_key("MARKET_API_KEY"))
ats_client       = genai.Client(api_key=_load_key("RESUME_API_KEY"))
interview_client = genai.Client(api_key=_load_key("INTERVIEW_API_KEY"))

app = FastAPI(
    title="🚀 Unified AI Career Platform",
    description="""
## All-in-one AI career assistant powered by **Gemini 2.5 Flash**

---

### 💬 Module 1 — Chat
General-purpose AI chat with conversation history.

### 📈 Module 2 — Market Trend Analyzer
Upload a resume PDF → get skill demand scores, job matches, salary insights, and a personalized learning path.

### 🚀 Module 3 — ATS Resume Analyzer
Upload a resume + paste a job description → semantic match score, ATS keyword score, skill gap analysis, and a day-by-day learning roadmap.
Includes **Candidate Mode** and **Recruiter Mode**.

### 🎯 Module 4 — AI Interview Guide
Generate interview questions for any role → simulate a live mock interview → get detailed performance feedback.

---
**Run locally:** `uvicorn main:app --reload --reload-dir .`  
**Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
""",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","have","has","had","do","does","did",
    "will","would","could","should","may","might","must","shall","can","need",
    "that","this","these","those","it","its","we","you","your","our","their",
    "from","by","as","if","so","not","no","nor","yet","both","either","about",
    "above","after","before","between","into","through","during","including",
    "without","within","along","following","across","behind","beyond","plus",
    "except","up","out","around","down","off","over","under","again","further",
    "then","once","more","also","just","than","other","such","any","all","each",
    "how","what","when","where","who","which","while","per","etc","ie","eg",
}

def gemini_text(prompt: str, client) -> str:
    """Call Gemini with a specific module client and return the text response."""
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()

def parse_json(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(io.BytesIO(file_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages).strip()

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'", examples=["user"])
    text: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's latest message")
    history: list[ChatMessage] = Field(default=[], description="Previous conversation turns")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI assistant reply")


def build_chat_conversation(message: str, history: list[ChatMessage]) -> str:
    """Build a plain-text conversation string for Gemini."""
    conversation = ""
    for msg in history:
        role = "User" if msg.role == "user" else "Assistant"
        conversation += f"{role}: {msg.text}\n"
    conversation += f"User: {message}\nAssistant:"
    return conversation

chat_tag = ["💬 Chat"]

@app.post(
    "/chat/message",
    response_model=ChatResponse,
    tags=chat_tag,
    summary="Send a message to the AI assistant",
    description="""
Send a message and optionally include conversation history.
The AI maintains context across turns through the `history` array.

**Example request:**
```json
{
  "message": "Explain what a transformer model is in simple terms.",
  "history": []
}
```
""",
)
async def chat_message(req: ChatRequest):
    try:
        conversation = build_chat_conversation(req.message, req.history)
        response     = chat_client.models.generate_content(model=GEMINI_MODEL, contents=conversation)
        reply        = response.text if response.text else "No response generated."
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def market_extract_skills(resume_text: str) -> list[str]:
    """Extract technical skills from resume text."""
    prompt = (
        "Extract all specific technical skills, tools, programming languages, "
        "frameworks and technologies from this resume.\n"
        "Be specific — return 'python' not 'programming'.\n"
        "Return ONLY valid JSON: {\"skills\": [\"python\", \"sql\", \"react\"]}\n"
        "No broad categories, no markdown fences.\n\n"
        f"Resume:\n{resume_text[:8000]}"
    )
    try:
        return parse_json(gemini_text(prompt, market_client)).get("skills", [])
    except Exception:
        return []


def market_analyze(resume_skills: list[str]) -> dict:
    """Run full market analysis for given skills via a single Gemini call."""
    prompt = f"""
You are a senior job market analyst with deep knowledge of current tech hiring trends (2024-2025).

The candidate has these skills: {", ".join(resume_skills)}

Perform a complete market analysis. Return ONLY valid JSON (no markdown):
{{
  "skill_demand": [
    {{"skill":"python","demand_score":95,"trend":"rising","level":"high","market_comment":"one line insight"}}
  ],
  "trending_skills": [
    {{"skill":"skill name","demand_score":90,"why_trending":"brief reason"}}
  ],
  "skill_gaps": [
    {{"skill":"missing skill","demand_score":85,"why_needed":"brief reason"}}
  ],
  "job_matches": [
    {{"title":"Job Title","match_pct":82,"required_skills":["s1","s2"],"missing_skills":["s3"],"avg_salary_usd":"120000-150000"}}
  ],
  "salary_insights": {{
    "current_estimated_range":"$X-$Y",
    "potential_range_with_upskilling":"$A-$B",
    "currency":"USD",
    "market_summary":"2-3 sentence salary analysis",
    "by_role":[{{"role":"name","min":"$X","avg":"$Y","max":"$Z"}}]
  }},
  "learning_path": [
    {{"skill":"skill to learn","priority":"high","estimated_time":"4 weeks","salary_impact":"+$10,000/yr","resource":"YouTube channel or course"}}
  ],
  "market_summary":"3-4 sentence overall assessment"
}}
Rules: demand_score 0-100 | trend: rising/stable/declining | level: high/medium/low
Top 8 job matches, top 8 trending skills, top 6 skill gaps, top 6 learning path items.
"""
    try:
        return parse_json(gemini_text(prompt, market_client))
    except Exception as e:
        logger.warning("Market analysis parse error: %s", e)
        return {}


# ── Routes ────────────────────────────────────────────────────────────────────

market_tag = ["📈 Market Trend Analyzer"]

@app.post(
    "/market/analyze",
    tags=market_tag,
    summary="Analyze job market from resume PDF",
    description="""
Upload a resume PDF to receive a **complete job market analysis** including:

- ✅ Skill demand scores (0–100) for each of your skills
- 📈 Top trending skills in the 2024–2025 market
- ❌ Critical skill gaps you're missing
- 💼 Best matching job roles with % fit
- 💰 Salary insights (current range + potential after upskilling)
- 🎯 Prioritized learning path with resources

**Form field:** `resume` — PDF file only
""",
)
async def market_analyze_route(
    resume: UploadFile = File(..., description="Resume PDF file"),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes  = await resume.read()
    resume_text = extract_text_from_pdf(file_bytes)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")

    skills = market_extract_skills(resume_text)
    if not skills:
        raise HTTPException(status_code=422, detail="Could not extract skills from the resume.")

    data = market_analyze(skills)
    if not data:
        raise HTTPException(status_code=500, detail="Market analysis failed. Please try again.")

    data["skills"] = skills
    return data


# ═════════════════════════════════════════════════════════════════════════════
#  MODULE 3 — ATS RESUME ANALYZER
# ═════════════════════════════════════════════════════════════════════════════

# ── Core logic ────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Get a Gemini embedding vector using the ATS module client."""
    result = ats_client.models.embed_content(model=EMBED_MODEL, contents=text)
    return result.embeddings[0].values


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    return 0.0 if (mag_a == 0 or mag_b == 0) else dot / (mag_a * mag_b)


def ats_semantic_score(resume_text: str, jd_text: str) -> float:
    """
    Chunk resume → embed each chunk + JD → cosine similarity → 0-100 score.
    Replaces Chroma + LangChain embeddings entirely (avoids SDK conflicts).
    """
    splitter   = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    chunks     = splitter.split_text(resume_text)
    if not chunks:
        return 0.0
    jd_vec     = get_embedding(jd_text[:3000])
    chunk_vecs = [get_embedding(c) for c in chunks[:12]]
    sims       = sorted([cosine_similarity(cv, jd_vec) for cv in chunk_vecs], reverse=True)
    avg        = sum(sims[:5]) / min(5, len(sims))
    return round(avg * 100, 2)


def ats_keyword_score(resume_text: str, jd_text: str) -> tuple[float, float]:
    """Keyword-based ATS score + keyword density."""
    resume_count = Counter(re.findall(r"\w+", resume_text.lower()))
    jd_keywords  = {w for w in set(re.findall(r"\w+", jd_text.lower()))
                    if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()}
    if not jd_keywords:
        return 0.0, 0.0
    matched          = sum(1 for kw in jd_keywords if resume_count[kw] > 0)
    stuffing_penalty = sum(resume_count[kw] - 10 for kw in jd_keywords if resume_count[kw] > 10)
    kw_density       = matched / len(jd_keywords)
    final            = max(0.0, kw_density - stuffing_penalty * 0.001)
    return round(final * 100, 2), round(kw_density * 100, 2)


def ats_extract_skills(text: str) -> set[str]:
    """Extract skills from resume or JD text."""
    prompt = (
        "Extract specific technical skills, tools, programming languages, frameworks, "
        "and technologies from the following text.\n"
        "Return ONLY valid JSON: {\"skills\": [\"python\", \"react\", \"sql\"]}\n"
        "No broad categories, no markdown fences.\n\n"
        f"Text:\n{text}"
    )
    try:
        parsed = parse_json(gemini_text(prompt, ats_client))
        return {s.lower().strip() for s in parsed.get("skills", []) if isinstance(s, str)}
    except Exception as e:
        logger.warning("Skills parse error: %s", e)
        return set()


def ats_debug_info(resume_text: str, jd_text: str) -> dict:
    """Return keyword debug info (matched / not matched)."""
    resume_count = Counter(re.findall(r"\w+", resume_text.lower()))
    jd_keywords  = {w for w in set(re.findall(r"\w+", jd_text.lower()))
                    if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()}
    matched      = {kw for kw in jd_keywords if resume_count[kw] > 0}
    return {"jd_keywords": sorted(jd_keywords), "matched": sorted(matched), "not_matched": sorted(jd_keywords - matched)}


def ats_learning_roadmap(missing_skills: list[str], existing_skills: list[str]) -> dict:
    """Generate a day-by-day learning roadmap for missing skills."""
    if not missing_skills:
        return {}
    prompt = f"""
You are a senior career coach. The candidate knows: {", ".join(existing_skills[:15])}
They are missing: {", ".join(missing_skills[:8])}
Assume 2 hours/day of study.

Return ONLY valid JSON (no markdown):
{{
  "overall": {{
    "total_days":75,"total_weeks":11,"hours_per_day":2,"difficulty":"Moderate",
    "summary":"One motivating sentence","recommended_order":["skill1","skill2"],"quick_wins":["skills under 2 weeks"]
  }},
  "skills": [
    {{
      "skill":"skill_name","why_important":"1 sentence","priority":"critical","difficulty":"moderate",
      "time_estimate":{{"beginner_days":10,"intermediate_days":15,"expert_days":20,"total_days":45,"time_note":"2 hrs/day"}},
      "approach":[
        {{"step":1,"action":"Docs + beginner tutorial","duration":"Days 1-10"}},
        {{"step":2,"action":"Build 2-3 small projects","duration":"Days 11-25"}},
        {{"step":3,"action":"Production patterns + interview prep","duration":"Days 26-45"}}
      ],
      "phases":[
        {{"phase":"beginner","days":"Days 1-10","daily_focus":"Core syntax","daily_goal":"Follow tutorial","phase_outcome":"Write basic programs"}},
        {{"phase":"intermediate","days":"Days 11-25","daily_focus":"Real projects","daily_goal":"Build weekly project","phase_outcome":"Working project"}},
        {{"phase":"expert","days":"Days 26-45","daily_focus":"Advanced patterns","daily_goal":"Production codebases","phase_outcome":"Job-ready"}}
      ],
      "milestones":["Write without syntax lookup","Deploy a project","Explain architecture","Debug real usage"],
      "tips":{{"do":["Code along tutorials","Build meaningful projects"],"dont":["Read without coding","Skip beginner phase"]}},
      "courses":{{
        "beginner":[{{"title":"Title","channel":"freeCodeCamp","search_query":"YouTube query","duration":"4 hours","what_you_learn":"Brief description"}}],
        "intermediate":[{{"title":"Title","channel":"Traversy Media","search_query":"YouTube query","duration":"6 hours","what_you_learn":"Brief description"}}],
        "expert":[{{"title":"Title","channel":"Fireship","search_query":"YouTube query","duration":"8 hours","what_you_learn":"Brief description"}}]
      }}
    }}
  ]
}}
Rules: priority: critical|high|medium|low | difficulty: easy|moderate|hard|very hard
Use real YouTube channels. 1-2 courses per stage.
"""
    try:
        return parse_json(gemini_text(prompt, ats_client))
    except Exception as e:
        logger.warning("Roadmap parse error: %s", e)
        return {}


def ats_recruiter_analysis(
    resume_text: str, jd_text: str,
    resume_skills: set[str], jd_skills: set[str],
    sem_score: float, ats_final: float,
) -> dict:
    """Run recruiter-grade AI analysis on the candidate."""
    matched   = resume_skills & jd_skills
    missing   = jd_skills - resume_skills
    match_pct = round(len(matched) / len(jd_skills) * 100, 1) if jd_skills else 0

    rule_flags = []
    if len(resume_text) < 500: rule_flags.append("Resume is very short — may lack detail")
    if match_pct < 30:         rule_flags.append(f"Only {match_pct}% skill overlap with JD")
    if ats_final < 40:         rule_flags.append("Low ATS score — may not pass automated screening")
    if sem_score < 40:         rule_flags.append("Low semantic match — content doesn't align with JD")

    prompt = f"""
You are a senior technical recruiter.
Resume skills: {sorted(resume_skills)} | JD required: {sorted(jd_skills)}
Matched: {sorted(matched)} | Missing: {sorted(missing)}
Skill match: {match_pct}% | Semantic: {sem_score}/100 | ATS: {ats_final}/100
Flags: {rule_flags}
Resume: {resume_text[:3000]}
JD: {jd_text[:2000]}

Return ONLY valid JSON (no markdown):
{{
  "verdict":"Strong Hire | Good Candidate | Maybe | Needs Improvement | Reject",
  "verdict_reason":"1-2 sentence justification",
  "overall_score":82,
  "scores":{{"skill_match":85,"experience_relevance":78,"communication_clarity":80,"technical_depth":75,"culture_fit_indicators":70}},
  "candidate_summary":"3-4 sentence summary",
  "strengths":["s1","s2","s3"],
  "red_flags":["f1","f2"],
  "skill_match_breakdown":{{"matched":["s1"],"missing_critical":["s2"],"missing_nice_to_have":["s3"],"bonus_skills":["s4"]}},
  "interview_questions":[{{"question":"...","reason":"why"}}],
  "hiring_recommendation":"2-3 sentence recommendation",
  "salary_band_fit":"entry | mid | senior | lead"
}}
"""
    try:
        result = parse_json(gemini_text(prompt, ats_client))
        result["_meta"] = {"sem_score": sem_score, "ats_score": ats_final, "match_pct": match_pct, "rule_flags": rule_flags}
        return result
    except Exception as e:
        logger.warning("Recruiter analysis parse error: %s", e)
        return {}


async def ats_shared_pipeline(file_bytes: bytes, jd_text: str) -> dict:
    """Shared pipeline: extract text → scores → skills."""
    resume_text = extract_text_from_pdf(file_bytes)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    resume_text = resume_text[:15000]
    jd_text     = jd_text.strip()[:10000]

    warnings = []
    jd_kw_count = len({w for w in set(re.findall(r"\w+", jd_text.lower()))
                        if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()})
    if jd_kw_count < 15:
        warnings.append(f"JD only has {jd_kw_count} keywords — scores may be unreliable.")

    sem_score             = ats_semantic_score(resume_text, jd_text)
    ats_final, kw_density = ats_keyword_score(resume_text, jd_text)
    resume_skills         = ats_extract_skills(resume_text)
    jd_skills             = ats_extract_skills(jd_text)

    return {
        "resume_text": resume_text, "jd_text": jd_text,
        "sem_score": sem_score, "ats_final": ats_final, "kw_density": kw_density,
        "resume_skills": resume_skills, "jd_skills": jd_skills, "warnings": warnings,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

ats_tag = ["🚀 ATS Resume Analyzer"]

@app.post(
    "/ats/candidate",
    tags=ats_tag,
    summary="Candidate mode — ATS scores + skill gap + learning roadmap",
    description="""
Upload your resume PDF and paste the job description to receive:

- 🎯 **Semantic match score** (0–100) — how well your resume content aligns with the JD
- 📊 **ATS keyword score** (0–100) — keyword match like automated ATS systems use
- 🔑 **Keyword density** — what % of JD keywords appear in your resume
- ✅ **Resume skills** — all skills detected in your resume
- 🎯 **JD skills** — all skills required by the job description
- ❌ **Missing skills** — skills in the JD that you don't have
- 🗓️ **Learning roadmap** — day-by-day plan with YouTube courses for every missing skill
- 🐛 **Debug info** — exact keywords matched/not matched

**Form fields:**
- `resume` — PDF file
- `job_description` — full job description text
""",
)
async def ats_candidate(
    resume: UploadFile = File(..., description="Resume PDF"),
    job_description: str = Form(..., description="Full job description text"),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    file_bytes    = await resume.read()
    data          = await ats_shared_pipeline(file_bytes, job_description)
    resume_skills = data["resume_skills"]
    jd_skills     = data["jd_skills"]
    missing       = sorted(jd_skills - resume_skills)
    roadmap       = ats_learning_roadmap(missing, list(resume_skills)) if missing else {}
    debug         = ats_debug_info(data["resume_text"], data["jd_text"])

    return {
        "warnings":        data["warnings"],
        "semantic_score":  data["sem_score"],
        "ats_score":       data["ats_final"],
        "keyword_density": data["kw_density"],
        "resume_skills":   sorted(resume_skills),
        "jd_skills":       sorted(jd_skills),
        "missing_skills":  missing,
        "roadmap":         roadmap,
        "debug":           debug,
    }


@app.post(
    "/ats/recruiter",
    tags=ats_tag,
    summary="Recruiter mode — hiring verdict + scorecard + interview questions",
    description="""
Upload a candidate resume PDF and job description to receive a **recruiter-grade AI evaluation**:

- ✅ / ⚠️ / ❌ **Hiring verdict** — Strong Hire / Good Candidate / Maybe / Needs Improvement / Reject
- 📊 **Score card** — Skill match, Experience relevance, Communication, Technical depth, Culture fit
- 🚩 **Red flags** — Issues detected by rule engine + AI
- 🎯 **Skill match breakdown** — Matched / Critical missing / Nice-to-have / Bonus skills
- 💬 **Interview questions** — Tailored questions to probe the candidate's gaps
- 📋 **Hiring recommendation** — Concrete next-step advice

**Form fields:**
- `resume` — PDF file
- `job_description` — full job description text
""",
)
async def ats_recruiter(
    resume: UploadFile = File(..., description="Candidate resume PDF"),
    job_description: str = Form(..., description="Full job description text"),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    file_bytes = await resume.read()
    data       = await ats_shared_pipeline(file_bytes, job_description)
    report     = ats_recruiter_analysis(
        data["resume_text"], data["jd_text"],
        data["resume_skills"], data["jd_skills"],
        data["sem_score"], data["ats_final"],
    )
    if not report:
        raise HTTPException(status_code=500, detail="Recruiter analysis failed. Please try again.")

    return {
        "warnings":        data["warnings"],
        "semantic_score":  data["sem_score"],
        "ats_score":       data["ats_final"],
        "keyword_density": data["kw_density"],
        "resume_skills":   sorted(data["resume_skills"]),
        "jd_skills":       sorted(data["jd_skills"]),
        "report":          report,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  MODULE 4 — AI INTERVIEW GUIDE
# ═════════════════════════════════════════════════════════════════════════════

# ── Pydantic models ───────────────────────────────────────────────────────────

class InterviewSetupRequest(BaseModel):
    role:       str                  = Field(...,    description="Job role / position", examples=["Senior Data Scientist"])
    experience: str                  = Field(...,    description="Experience level",    examples=["Senior Level (5-8 yrs)"])
    focus:      list[str]            = Field([],     description="Optional focus areas", examples=[["Machine Learning", "System Design"]])

class InterviewChatRequest(BaseModel):
    role:     str        = Field(..., description="Job role being interviewed for")
    question: str        = Field(..., description="The interview question that was asked")
    answer:   str        = Field(..., description="The candidate's answer")
    history:  list[dict] = Field([], description="Previous Q&A pairs: [{question, answer}]")

class InterviewFeedbackRequest(BaseModel):
    role:      str        = Field(..., description="Job role")
    questions: list[dict] = Field(..., description="Full question objects returned by /interview/questions")
    answers:   list[str]  = Field(..., description="Candidate answers in the same order as questions. Use '[Skipped]' for skipped questions.")


# ── Core logic ────────────────────────────────────────────────────────────────

def interview_generate_questions(role: str, experience: str, focus: list[str]) -> list:
    """Generate 7 mixed interview questions for a role."""
    focus_str = f"Focus especially on: {', '.join(focus)}." if focus else ""
    prompt = f"""
You are an expert technical interviewer.
Generate 7 interview questions for a {experience} {role} candidate.
Mix: 2 behavioral, 3 technical, 1 system design, 1 situational. {focus_str}

Return ONLY valid JSON (no markdown):
{{
  "questions": [
    {{"id":1,"type":"technical","question":"...","hint":"What the interviewer is looking for","difficulty":"easy | medium | hard"}}
  ]
}}
"""
    try:
        return parse_json(gemini_text(prompt, interview_client)).get("questions", [])
    except Exception as e:
        logger.warning("Questions parse error: %s", e)
        return []


def interview_chat(question: str, answer: str, role: str, history: list[dict]) -> str:
    """Generate an interviewer follow-up after a candidate answer."""
    history_text = ""
    for h in history[-4:]:
        history_text += f"Q: {h.get('question','')}\nA: {h.get('answer','')}\n\n"

    prompt = f"""
You are a professional {role} interviewer conducting a mock interview.
Previous exchanges:
{history_text}
Current question: {question}
Candidate's answer: {answer}

Respond as a real interviewer:
- Acknowledge briefly (1 sentence)
- Ask a natural follow-up or probe deeper
- Keep response to 2-4 sentences, professional but conversational
- Do NOT give scores or feedback yet
"""
    return gemini_text(prompt, interview_client)


def interview_generate_feedback(role: str, questions: list[dict], answers: list[str]) -> dict:
    """Generate comprehensive post-interview performance feedback."""
    qa_pairs = ""
    for i, (q, a) in enumerate(zip(questions, answers)):
        qa_pairs += f"Q{i+1} ({q.get('type','')}, {q.get('difficulty','')}): {q.get('question','')}\nAnswer: {a}\n\n"

    prompt = f"""
You are a senior {role} interviewer providing detailed post-interview feedback.
Interview transcript:
{qa_pairs}

Return ONLY valid JSON (no markdown):
{{
  "overall_score":75,"communication_score":80,"technical_score":70,"confidence_score":75,
  "verdict":"Strong Candidate | Good Candidate | Needs Improvement | Not Ready",
  "summary":"2-3 sentence overall assessment",
  "strengths":["strength 1","strength 2","strength 3"],
  "weaknesses":["weakness 1","weakness 2"],
  "suggestions":["suggestion 1","suggestion 2","suggestion 3"],
  "per_question":[
    {{"question_id":1,"score":80,"comment":"brief feedback","ideal_answer_hint":"what a great answer includes"}}
  ],
  "next_steps":["action 1","action 2","action 3"]
}}
"""
    try:
        return parse_json(gemini_text(prompt, interview_client))
    except Exception as e:
        logger.warning("Feedback parse error: %s", e)
        return {}


# ── Routes ────────────────────────────────────────────────────────────────────

interview_tag = ["🎯 AI Interview Guide"]

@app.post(
    "/interview/questions",
    tags=interview_tag,
    summary="Generate 7 interview questions for a role",
    description="""
Generate a mixed set of **7 interview questions** tailored to the role and experience level.

Mix of: `2 behavioral` + `3 technical` + `1 system design` + `1 situational`

Each question includes:
- `id` — question number
- `type` — behavioral / technical / system design / situational
- `question` — the actual question
- `hint` — what the interviewer is looking for
- `difficulty` — easy / medium / hard

**Store the returned `questions` array** — you'll need to pass it to `/interview/feedback` later.
""",
)
async def interview_questions(req: InterviewSetupRequest):
    if not req.role.strip():
        raise HTTPException(status_code=400, detail="Role cannot be empty.")

    questions = interview_generate_questions(req.role.strip(), req.experience, req.focus)
    if not questions:
        raise HTTPException(status_code=500, detail="Could not generate questions. Please try again.")

    return {"questions": questions}


@app.post(
    "/interview/chat",
    tags=interview_tag,
    summary="Get AI interviewer follow-up after a candidate answer",
    description="""
After the candidate answers a question, call this endpoint to get a **natural interviewer follow-up**.

The AI will:
- Acknowledge the answer briefly
- Ask a deeper follow-up question or probe for more detail
- Stay in character as a professional interviewer (no scores/feedback)

Pass `history` as the list of previous question/answer pairs for context.
""",
)
async def interview_chat_route(req: InterviewChatRequest):
    if not req.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    followup = interview_chat(req.question, req.answer.strip(), req.role, req.history)
    return {"followup": followup}


@app.post(
    "/interview/feedback",
    tags=interview_tag,
    summary="Get full performance feedback after the interview",
    description="""
After all questions are answered, call this endpoint for **comprehensive performance feedback**.

Pass:
- `questions` — the full question objects from `/interview/questions`
- `answers` — your answers in the **same order** (use `"[Skipped]"` for skipped questions)

Returns:
- Overall / communication / technical / confidence scores (0–100)
- Verdict — Strong Candidate / Good Candidate / Needs Improvement / Not Ready
- Strengths, weaknesses, and actionable suggestions
- Per-question breakdown with score, comment, and ideal answer hint
- Next steps for improvement
""",
)
async def interview_feedback(req: InterviewFeedbackRequest):
    if not req.questions:
        raise HTTPException(status_code=400, detail="Questions list cannot be empty.")
    if not req.answers:
        raise HTTPException(status_code=400, detail="Answers list cannot be empty.")

    fb = interview_generate_feedback(req.role, req.questions, req.answers)
    if not fb:
        raise HTTPException(status_code=500, detail="Could not generate feedback. Please try again.")

    return fb


# ═════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    tags=["⚙️ System"],
    summary="Health check",
    description="Returns `{status: ok}` if the API is running.",
)
async def health():
    return {
        "status": "ok",
        "modules": {
            "chat":      {"key_env": "CHAT_GEMINI_KEY",      "endpoints": ["POST /chat/message"]},
            "market":    {"key_env": "MARKET_GEMINI_KEY",    "endpoints": ["POST /market/analyze"]},
            "ats":       {"key_env": "ATS_GEMINI_KEY",       "endpoints": ["POST /ats/candidate", "POST /ats/recruiter"]},
            "interview": {"key_env": "INTERVIEW_GEMINI_KEY", "endpoints": ["POST /interview/questions", "POST /interview/chat", "POST /interview/feedback"]},
        },
        "model": GEMINI_MODEL,
    }


@app.get(
    "/",
    tags=["⚙️ System"],
    summary="API info",
    description="Returns a quick summary of all available endpoints.",
)
async def root():
    return {
        "title":       "🚀 Unified AI Career Platform",
        "version":     "4.0.0",
        "swagger_ui":  "/docs",
        "redoc":       "/redoc",
        "endpoints": {
            "chat":      ["POST /chat/message"],
            "market":    ["POST /market/analyze"],
            "ats":       ["POST /ats/candidate", "POST /ats/recruiter"],
            "interview": ["POST /interview/questions", "POST /interview/chat", "POST /interview/feedback"],
        },
    }