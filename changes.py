import os
import json
import re
import uuid
import logging
from collections import Counter

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

import google.generativeai as genai

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="AI Resume ATS Analyzer", page_icon="🚀", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [data-testid="stAppViewContainer"] { background-color: #0a0a0f; color: #e8e4dc; font-family: 'Syne', sans-serif; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0f0f1a !important; border-right: 1px solid #1e1e2e; }
h1, h2, h3 { font-family: 'Syne', sans-serif; font-weight: 800; }
.metric-card { background: #111120; border: 1px solid #1e1e2e; border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 1rem; }
.metric-value { font-size: 3rem; font-weight: 800; font-family: 'IBM Plex Mono', monospace; line-height: 1; }
.metric-label { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: #555; margin-top: 0.5rem; }
.score-bar-track { background: #1e1e2e; border-radius: 999px; height: 7px; margin-top: 0.75rem; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 999px; }
.score-high { color: #00e5a0; } .score-mid { color: #f5c542; } .score-low { color: #ff5e5e; }
.pill-container { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; }
.pill { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; padding: 0.2rem 0.65rem; border-radius: 999px; font-weight: 500; }
.pill-green  { background:#00e5a015; border:1px solid #00e5a040; color:#00e5a0; }
.pill-red    { background:#ff5e5e15; border:1px solid #ff5e5e40; color:#ff5e5e; }
.pill-blue   { background:#4f9eff15; border:1px solid #4f9eff40; color:#4f9eff; }
.pill-yellow { background:#f5c54215; border:1px solid #f5c54240; color:#f5c542; }
.section-card { background: #111120; border: 1px solid #1e1e2e; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }
.course-card { background: #111120; border: 1px solid #1e1e2e; border-radius: 12px; padding: 1.25rem; margin-bottom: 0.75rem; }
.course-card:hover { border-color: #00e5a040; }
.course-tag-beginner     { background:#00e5a015; border:1px solid #00e5a040; color:#00e5a0; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:999px; font-family:'IBM Plex Mono',monospace; }
.course-tag-intermediate { background:#f5c54215; border:1px solid #f5c54240; color:#f5c542; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:999px; font-family:'IBM Plex Mono',monospace; }
.course-tag-expert       { background:#ff5e5e15; border:1px solid #ff5e5e40; color:#ff5e5e; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:999px; font-family:'IBM Plex Mono',monospace; }
[data-testid="stFileUploader"] { background: #001a12; border: 1px dashed #00e5a030; border-radius: 12px; padding: 0.5rem; }
textarea { background: #111120 !important; border: 1px solid #1e1e2e !important; border-radius: 8px !important; color: #e8e4dc !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.85rem !important; }
.stButton > button { background: #00e5a0 !important; color: #0a0a0f !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; width: 100% !important; padding: 0.6rem 2rem !important; }
.stButton > button:hover { opacity: 0.85 !important; }
hr { border-color: #1e1e2e; }

/* Recruiter Mode styles */
.recruiter-banner { background: linear-gradient(135deg, #0d0020, #1a0035); border: 1px solid #6f3cff40; border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem; }
.recruiter-badge  { background:#6f3cff20; border:1px solid #6f3cff60; color:#a78bfa; font-size:0.65rem; padding:0.2rem 0.6rem; border-radius:999px; font-family:'IBM Plex Mono',monospace; letter-spacing:0.15em; }
.verdict-hire     { background:#00e5a010; border:2px solid #00e5a050; border-radius:12px; padding:1.5rem; text-align:center; }
.verdict-maybe    { background:#f5c54210; border:2px solid #f5c54250; border-radius:12px; padding:1.5rem; text-align:center; }
.verdict-reject   { background:#ff5e5e10; border:2px solid #ff5e5e50; border-radius:12px; padding:1.5rem; text-align:center; }
.flag-card        { background:#111120; border-left:3px solid #ff5e5e; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-bottom:0.5rem; font-size:0.88rem; }
.strength-card    { background:#111120; border-left:3px solid #00e5a0; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-bottom:0.5rem; font-size:0.88rem; }
.history-card     { background:#111120; border:1px solid #1e1e2e; border-radius:10px; padding:1rem; margin-bottom:0.75rem; cursor:pointer; }
.history-card:hover { border-color:#6f3cff40; }

/* ── Progress Tracker styles ── */
.tracker-banner {
    background: linear-gradient(135deg, #001220, #001a2e);
    border: 1px solid #4f9eff30;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.tracker-badge {
    background:#4f9eff20; border:1px solid #4f9eff60; color:#4f9eff;
    font-size:0.65rem; padding:0.2rem 0.6rem; border-radius:999px;
    font-family:'IBM Plex Mono',monospace; letter-spacing:0.15em;
}
.skill-progress-card {
    background: #111120;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.skill-progress-card.ready-expert {
    border-color: #00e5a060;
    background: linear-gradient(135deg, #001a12, #111120);
}
.skill-progress-card.stay-intermediate {
    border-color: #f5c54240;
}
.skill-progress-card.keep-beginner {
    border-color: #ff5e5e30;
}
.verdict-ready {
    background: #00e5a015;
    border: 2px solid #00e5a060;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
    margin-top: 0.75rem;
}
.verdict-almost {
    background: #f5c54215;
    border: 2px solid #f5c54260;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
    margin-top: 0.75rem;
}
.verdict-notyet {
    background: #ff5e5e10;
    border: 2px solid #ff5e5e40;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
    margin-top: 0.75rem;
}
.checkpoint-item {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    background: #0a0a0f;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    font-size: 0.83rem;
}
.checkpoint-done { border-left: 3px solid #00e5a0; }
.checkpoint-pending { border-left: 3px solid #444; opacity: 0.6; }
.overall-progress-bar {
    background: #1e1e2e;
    border-radius: 999px;
    height: 12px;
    overflow: hidden;
    margin: 0.5rem 0;
}
.overall-progress-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.4s ease;
}
</style>
""", unsafe_allow_html=True)

# ── API Key ───────────────────────────────────────────────────────────────────
api_key = os.getenv("GOOGLE_GEMINI_KEY")
if not api_key:
    st.error("❌ GOOGLE_GEMINI_KEY not found. Please add it to your .env file.")
    st.stop()

# ── Session State ─────────────────────────────────────────────────────────────
if "mode"              not in st.session_state: st.session_state.mode              = "candidate"
if "recruiter_history" not in st.session_state: st.session_state.recruiter_history = []
if "ats_results"       not in st.session_state: st.session_state.ats_results       = None
if "recruiter_report"  not in st.session_state: st.session_state.recruiter_report  = None
if "progress_data"     not in st.session_state: st.session_state.progress_data     = {}
# progress_data structure: { "skill_name": { "checkpoints": {checkpoint_key: bool}, "percent": int } }

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚀 ATS Analyzer")
    st.markdown("---")
    st.markdown("### 🔀 Switch Mode")
    mode_choice = st.radio(
        "Select Mode",
        ["👤 Candidate Mode", "🏢 Recruiter Mode", "📊 Progress Tracker"],
        index=["candidate","recruiter","progress"].index(st.session_state.mode),
        label_visibility="collapsed"
    )
    if "Candidate" in mode_choice:
        st.session_state.mode = "candidate"
    elif "Recruiter" in mode_choice:
        st.session_state.mode = "recruiter"
    else:
        st.session_state.mode = "progress"

    st.markdown("---")

    if st.session_state.mode == "candidate":
        st.markdown("""
**Candidate Mode:**
1. Upload resume PDF
2. Paste job description
3. Get ATS score + skill gaps
4. YouTube learning roadmap
        """)
    elif st.session_state.mode == "recruiter":
        st.markdown("""
**Recruiter Mode:**
1. Upload candidate resume PDF
2. Paste job description
3. Get structured analysis:
   - Hire / Maybe / Reject verdict
   - Candidate score card
   - Skill match breakdown
   - Red flags detection
   - Session history
        """)
        if st.session_state.recruiter_history:
            st.markdown(f"📋 **{len(st.session_state.recruiter_history)} candidate(s)** reviewed this session")
            if st.button("🗑️ Clear History"):
                st.session_state.recruiter_history = []
                st.rerun()
    else:
        st.markdown("""
**Progress Tracker:**
1. Enter the skills you're learning
2. Check off completed milestones
3. AI evaluates your progress
4. Get upgrade recommendation:
   - Stay in Beginner
   - Move to Intermediate
   - Ready for Expert
        """)
        if st.session_state.progress_data:
            total_skills = len(st.session_state.progress_data)
            ready_count  = sum(
                1 for s in st.session_state.progress_data.values()
                if s.get("percent", 0) >= 80
            )
            st.markdown(f"📈 **{ready_count}/{total_skills}** skills ready to advance")
        if st.button("🗑️ Reset Tracker"):
            st.session_state.progress_data = {}
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
if st.session_state.mode == "candidate":
    st.markdown("# 🚀 AI Resume ATS Analyzer")
    st.markdown("<p style='color:#555; margin-top:-0.5rem;'>Semantic + keyword matching powered by Gemini</p>", unsafe_allow_html=True)
elif st.session_state.mode == "recruiter":
    st.markdown("# 🏢 Recruiter Dashboard")
    st.markdown("<p style='color:#a78bfa; margin-top:-0.5rem;'>AI-powered candidate evaluation & scoring</p>", unsafe_allow_html=True)
else:
    st.markdown("# 📊 Learning Progress Tracker")
    st.markdown("<p style='color:#4f9eff; margin-top:-0.5rem;'>Track your learning journey — AI tells you when you're ready to level up</p>", unsafe_allow_html=True)

st.markdown("---")




def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    return "".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_skills(text: str, model) -> set:
    prompt = (
        "Extract specific technical skills, tools, programming languages, frameworks, "
        "and technologies from the following text.\n"
        "Be specific — return 'python' not 'programming'.\n"
        "Return ONLY valid JSON: {\"skills\": [\"python\", \"react\", \"sql\"]}\n"
        "No broad categories, no markdown fences.\n\n"
        f"Text:\n{text}"
    )
    response = model.generate_content(prompt)
    cleaned  = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        return {s.lower().strip() for s in parsed.get("skills", []) if isinstance(s, str)}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Skills parse error: %s", e)
        return set()


def get_youtube_roadmap(missing_skills: list, model) -> dict:
    if not missing_skills:
        return {}
    skills_str = ", ".join(missing_skills[:8])
    prompt = f"""
You are an expert career coach. The user is missing: {skills_str}

For EACH skill suggest TOP YouTube courses across 3 stages.
Return ONLY valid JSON (no markdown):
{{
  "roadmap": [
    {{
      "skill": "skill_name",
      "why_important": "1 sentence",
      "beginner":     [{{ "title":"...","channel":"...","search_query":"...","duration":"...","what_you_learn":"..." }}],
      "intermediate": [{{ "title":"...","channel":"...","search_query":"...","duration":"...","what_you_learn":"..." }}],
      "expert":       [{{ "title":"...","channel":"...","search_query":"...","duration":"...","what_you_learn":"..." }}]
    }}
  ]
}}
Rules: only real YouTube channels, 1-2 items per stage, what_you_learn under 15 words.
"""
    response = model.generate_content(prompt)
    cleaned  = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        return {item["skill"]: item for item in data.get("roadmap", [])}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Roadmap parse error: %s", e)
        return {}


def get_progress_checkpoints(skill: str, current_level: str, model) -> dict:
    """
    Generate a checklist of milestones for a skill at a given level.
    Used by the Progress Tracker to define what 'done' looks like.
    """
    prompt = f"""
You are a technical career mentor. Generate a progress checklist for someone learning "{skill}" at the "{current_level}" level.

Return ONLY valid JSON (no markdown):
{{
  "skill": "{skill}",
  "level": "{current_level}",
  "checkpoints": [
    {{
      "id": "cp1",
      "label": "Short milestone statement (max 12 words)",
      "weight": 15
    }}
  ],
  "ready_threshold": 75,
  "next_level": "intermediate or expert or mastered",
  "upgrade_advice": "1-2 sentence advice on when and how to move to the next level"
}}

Rules:
- Provide exactly 6-8 checkpoints that cover the full {current_level} phase
- weight values must sum to 100
- Checkpoints should be concrete and self-verifiable
- For beginner: syntax basics, hello world, simple project, core concepts, etc.
- For intermediate: real projects, integrations, debugging, best practices, etc.
- For expert: system design, optimization, production usage, advanced patterns, etc.
- ready_threshold = minimum % completion to be considered ready to advance (usually 75-80)
"""
    response = model.generate_content(prompt)
    cleaned  = response.text.strip().replace("```json","").replace("```","").strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Checkpoint parse error: %s", e)
        return {}


def get_ai_upgrade_recommendation(skill: str, current_level: str, completed_checkpoints: list,
                                   pending_checkpoints: list, percent: int, model) -> dict:
    """
    AI evaluates the candidate's self-reported progress and gives a verdict:
    ready_to_advance / almost_there / keep_going
    """
    prompt = f"""
You are a strict but fair technical mentor evaluating a learner's readiness to advance.

Skill: {skill}
Current Level: {current_level}
Overall completion: {percent}%
Completed milestones: {completed_checkpoints}
Pending milestones: {pending_checkpoints}

Based on what they've completed vs what they've skipped, assess:
1. Are they genuinely ready to move to the next level?
2. What specific gaps remain?
3. What should they do before advancing?

Return ONLY valid JSON (no markdown):
{{
  "verdict": "ready_to_advance | almost_there | keep_going",
  "confidence": 85,
  "summary": "2-3 sentence honest assessment of where they stand",
  "missing_gaps": ["specific gap 1", "specific gap 2"],
  "action_items": ["concrete next step 1", "concrete next step 2", "concrete next step 3"],
  "estimated_days_to_ready": 5,
  "encouragement": "One motivating sentence"
}}

Be honest — don't approve advancement if critical milestones are missing.
"""
    response = model.generate_content(prompt)
    cleaned  = response.text.strip().replace("```json","").replace("```","").strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Upgrade recommendation parse error: %s", e)
        return {}


def run_recruiter_analysis(resume_text, jd_text, resume_skills, jd_skills, sem_score, ats_final, model) -> dict:
    matched   = resume_skills & jd_skills
    missing   = jd_skills - resume_skills
    match_pct = round(len(matched) / len(jd_skills) * 100, 1) if jd_skills else 0

    rule_flags = []
    if len(resume_text) < 500:
        rule_flags.append("Resume is very short — may lack detail")
    if match_pct < 30:
        rule_flags.append(f"Only {match_pct}% skill overlap with JD requirements")
    if ats_final < 40:
        rule_flags.append("Low ATS keyword score — resume may not pass automated screening")
    if sem_score < 40:
        rule_flags.append("Low semantic match — resume content doesn't align well with JD")

    prompt = f"""
You are a senior technical recruiter evaluating a candidate.
CANDIDATE DATA:
- Resume skills: {sorted(resume_skills)}
- JD required skills: {sorted(jd_skills)}
- Matched skills: {sorted(matched)}
- Missing skills: {sorted(missing)}
- Skill match: {match_pct}%
- Semantic match score: {sem_score}/100
- ATS keyword score: {ats_final}/100
- Pre-analysis flags: {rule_flags}
Resume excerpt: {resume_text[:3000]}
Job Description: {jd_text[:2000]}

Return ONLY valid JSON (no markdown):
{{
  "verdict": "Strong Hire | Good Candidate | Maybe | Needs Improvement | Reject",
  "verdict_reason": "1-2 sentence justification",
  "overall_score": 82,
  "scores": {{"skill_match": 85,"experience_relevance": 78,"communication_clarity": 80,"technical_depth": 75,"culture_fit_indicators": 70}},
  "candidate_summary": "3-4 sentence recruiter summary",
  "strengths": ["strength 1","strength 2","strength 3"],
  "red_flags": ["flag 1","flag 2"],
  "skill_match_breakdown": {{
    "matched": ["skill1"],"missing_critical": ["skill2"],"missing_nice_to_have": ["skill3"],"bonus_skills": ["skill4"]
  }},
  "interview_questions": [{{"question": "...","reason": "why ask this"}}],
  "hiring_recommendation": "2-3 sentence recommendation",
  "salary_band_fit": "entry | mid | senior | lead"
}}
"""
    response = model.generate_content(prompt)
    cleaned  = response.text.strip().replace("```json","").replace("```","").strip()
    try:
        result = json.loads(cleaned)
        result["_meta"] = {"sem_score": sem_score, "ats_score": ats_final, "match_pct": match_pct, "rule_flags": rule_flags}
        return result
    except:
        return {}


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


def ats_score(resume_text: str, jd_text: str) -> tuple[float, float]:
    resume_words = re.findall(r"\w+", resume_text.lower())
    jd_words     = re.findall(r"\w+", jd_text.lower())
    resume_count = Counter(resume_words)
    jd_keywords  = {w for w in set(jd_words) if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()}
    if not jd_keywords:
        return 0.0, 0.0
    matched_keywords = sum(1 for kw in jd_keywords if resume_count[kw] > 0)
    stuffing_penalty = sum(resume_count[kw] - 10 for kw in jd_keywords if resume_count[kw] > 10)
    keyword_density  = matched_keywords / len(jd_keywords)
    final            = max(0.0, keyword_density - stuffing_penalty * 0.001)
    return round(final * 100, 2), round(keyword_density * 100, 2)


def build_chroma(text: str, embeddings) -> Chroma:
    splitter  = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    documents = splitter.create_documents([text])
    return Chroma.from_documents(documents=documents, embedding=embeddings,
                                 collection_name=f"resume_{uuid.uuid4().hex}")


def semantic_match_score(resume_store, jd_text: str) -> float:
    results = resume_store.similarity_search_with_score(jd_text, k=5)
    if not results:
        return 0.0
    avg_distance = sum(score for _, score in results) / len(results)
    return round(1 / (1 + avg_distance) * 100, 2)


def score_card(label: str, value: float):
    css   = "score-high" if value >= 70 else ("score-mid" if value >= 40 else "score-low")
    color = "#00e5a0"    if value >= 70 else ("#f5c542"   if value >= 40 else "#ff5e5e")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {css}">{value}%</div>
        <div class="metric-label">{label}</div>
        <div class="score-bar-track">
            <div class="score-bar-fill" style="width:{value}%; background:{color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_course_card(course: dict, stage: str):
    tag_class = f"course-tag-{stage}"
    yt_url    = f"https://www.youtube.com/results?search_query={course.get('search_query','').replace(' ', '+')}"
    st.markdown(f"""
    <div class="course-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem">
            <div style="font-weight:700;font-size:0.9rem;color:#e8e4dc;">{course.get('title','')}</div>
            <span class="{tag_class}">{stage.upper()}</span>
        </div>
        <div style="font-size:0.78rem;color:#4f9eff;font-family:'IBM Plex Mono',monospace;margin-bottom:0.3rem">📺 {course.get('channel','')}</div>
        <div style="font-size:0.78rem;color:#888;margin-bottom:0.5rem">{course.get('what_you_learn','')}</div>
        <div style="display:flex;gap:1rem;align-items:center;">
            <span style="font-size:0.72rem;color:#555;">⏱ {course.get('duration','')}</span>
            <a href="{yt_url}" target="_blank" style="font-size:0.72rem;color:#ff5e5e;text-decoration:none;font-family:'IBM Plex Mono',monospace;">🔴 Search on YouTube →</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_recruiter_score_bar(label: str, score: int):
    color = "#00e5a0" if score >= 75 else ("#f5c542" if score >= 50 else "#ff5e5e")
    st.markdown(f"""
    <div style='margin-bottom:0.75rem'>
        <div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.3rem'>
            <span style='color:#888'>{label}</span>
            <span style='font-family:IBM Plex Mono,monospace;color:{color};font-weight:700'>{score}/100</span>
        </div>
        <div style='background:#1e1e2e;border-radius:999px;height:6px;overflow:hidden'>
            <div style='width:{score}%;height:100%;background:{color};border-radius:999px;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED ANALYSIS PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_shared_pipeline(uploaded_file, job_description):
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    embeddings   = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=api_key)

    with st.spinner("Extracting resume text..."):
        resume_text = extract_text_from_pdf(uploaded_file)
    if not resume_text:
        st.error("Could not extract text from PDF.")
        st.stop()
    if len(resume_text) > 15000:
        st.warning("Resume truncated to 15,000 characters.")
        resume_text = resume_text[:15000]

    jd_text = job_description.strip()
    if len(jd_text) > 10000:
        st.warning("JD truncated to 10,000 characters.")
        jd_text = jd_text[:10000]

    jd_keyword_count = len({w for w in set(re.findall(r"\w+", jd_text.lower()))
                            if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()})
    if jd_keyword_count < 15:
        st.warning(f"⚠️ JD only has **{jd_keyword_count} keywords** — scores may be unreliable.")

    with st.spinner("Building semantic index..."):
        resume_store = build_chroma(resume_text, embeddings)
    with st.spinner("Calculating semantic match..."):
        sem_score = semantic_match_score(resume_store, jd_text)

    ats_final, kw_density = ats_score(resume_text, jd_text)

    with st.spinner("Extracting skills via Gemini..."):
        resume_skills = extract_skills(resume_text, gemini_model)
        jd_skills     = extract_skills(jd_text, gemini_model)

    return {
        "resume_text": resume_text, "jd_text": jd_text,
        "sem_score": sem_score, "ats_final": ats_final, "kw_density": kw_density,
        "resume_skills": resume_skills, "jd_skills": jd_skills,
        "gemini_model": gemini_model,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER MODE
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.mode == "progress":

    # Banner
    st.markdown("""
    <div class="tracker-banner">
        <span style='font-size:1.5rem'>📊</span>
        <div>
            <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.3rem'>
                <span style='font-weight:700;font-size:1rem;color:#e8e4dc'>Learning Progress Tracker</span>
                <span class="tracker-badge">ACTIVE</span>
            </div>
            <div style='font-size:0.82rem;color:#666'>
                Check off milestones → AI evaluates your readiness → Get level-up recommendation
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 1: Add skills to track ───────────────────────────────────────────
    st.markdown("### ➕ Add a Skill to Track")

    add_col1, add_col2, add_col3 = st.columns([2, 1.5, 1])
    with add_col1:
        new_skill = st.text_input("Skill name", placeholder="e.g. React, Docker, FastAPI...",
                                   label_visibility="collapsed")
    with add_col2:
        new_level = st.selectbox("Current level", ["beginner", "intermediate", "expert"],
                                  label_visibility="collapsed")
    with add_col3:
        add_skill_btn = st.button("➕ Add Skill")

    if add_skill_btn and new_skill.strip():
        skill_key = new_skill.strip().lower()
        if skill_key not in st.session_state.progress_data:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            with st.spinner(f"Generating checkpoints for {new_skill}..."):
                checkpoint_data = get_progress_checkpoints(new_skill.strip(), new_level, model)

            if checkpoint_data:
                # Initialize all checkpoints as unchecked
                checks = {cp["id"]: False for cp in checkpoint_data.get("checkpoints", [])}
                st.session_state.progress_data[skill_key] = {
                    "display_name":   new_skill.strip(),
                    "level":          new_level,
                    "checkpoints":    checkpoint_data.get("checkpoints", []),
                    "checked":        checks,
                    "threshold":      checkpoint_data.get("ready_threshold", 75),
                    "next_level":     checkpoint_data.get("next_level", ""),
                    "upgrade_advice": checkpoint_data.get("upgrade_advice", ""),
                    "ai_verdict":     None,
                    "percent":        0,
                }
                st.success(f"✅ Added **{new_skill}** at **{new_level}** level with {len(checks)} checkpoints!")
                st.rerun()
            else:
                st.error("Could not generate checkpoints. Try again.")
        else:
            st.warning(f"**{new_skill}** is already being tracked.")

    st.markdown("")

    # ── Step 2: Skill progress cards ──────────────────────────────────────────
    if not st.session_state.progress_data:
        st.markdown("""
        <div style='background:#111120;border:1px dashed #1e1e2e;border-radius:12px;
                    padding:3rem;text-align:center;color:#444'>
            <div style='font-size:2rem;margin-bottom:0.75rem'>📚</div>
            <div style='font-size:0.9rem'>No skills added yet.<br/>
            Add a skill above to start tracking your progress.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("---")
        st.markdown("### 📋 Your Learning Progress")

        # Overall summary bar
        all_percents = [v.get("percent", 0) for v in st.session_state.progress_data.values()]
        avg_overall  = round(sum(all_percents) / len(all_percents)) if all_percents else 0
        ov_color     = "#00e5a0" if avg_overall >= 75 else ("#f5c542" if avg_overall >= 40 else "#ff5e5e")

        st.markdown(f"""
        <div style='background:#111120;border:1px solid #1e1e2e;border-radius:12px;
                    padding:1.25rem 1.5rem;margin-bottom:1.5rem'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem'>
                <span style='font-size:0.72rem;letter-spacing:0.15em;text-transform:uppercase;
                             color:#555;font-family:IBM Plex Mono,monospace'>Overall Progress Across All Skills</span>
                <span style='font-family:IBM Plex Mono,monospace;font-size:1.6rem;font-weight:800;
                             color:{ov_color}'>{avg_overall}%</span>
            </div>
            <div class="overall-progress-bar">
                <div class="overall-progress-fill" style="width:{avg_overall}%;background:{ov_color}"></div>
            </div>
            <div style='font-size:0.7rem;color:#555;font-family:IBM Plex Mono,monospace;margin-top:0.3rem'>
                Tracking {len(st.session_state.progress_data)} skill(s) — check off milestones to update
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Per-skill cards
        for skill_key, skill_data in st.session_state.progress_data.items():
            display_name   = skill_data["display_name"]
            current_level  = skill_data["level"]
            checkpoints    = skill_data["checkpoints"]
            checked        = skill_data["checked"]
            threshold      = skill_data["threshold"]
            next_level     = skill_data.get("next_level", "")
            upgrade_advice = skill_data.get("upgrade_advice", "")
            ai_verdict     = skill_data.get("ai_verdict", None)

            # Calculate current percent from checked weights
            total_weight   = sum(cp["weight"] for cp in checkpoints)
            checked_weight = sum(cp["weight"] for cp in checkpoints if checked.get(cp["id"], False))
            percent        = round(checked_weight / total_weight * 100) if total_weight else 0

            # Update stored percent
            st.session_state.progress_data[skill_key]["percent"] = percent

            # Card CSS class based on progress
            if percent >= threshold:
                card_class = "ready-expert"
                bar_color  = "#00e5a0"
            elif percent >= 50:
                card_class = "stay-intermediate"
                bar_color  = "#f5c542"
            else:
                card_class = "keep-beginner"
                bar_color  = "#ff5e5e"

            level_icon = {"beginner":"🟢","intermediate":"🟡","expert":"🔴"}.get(current_level, "📌")

            st.markdown(f"""
            <div class="skill-progress-card {card_class}">
                <div style='display:flex;justify-content:space-between;align-items:flex-start;
                            flex-wrap:wrap;gap:0.5rem;margin-bottom:0.75rem'>
                    <div>
                        <div style='font-size:1.05rem;font-weight:800'>
                            {level_icon} {display_name.title()}
                        </div>
                        <div style='font-size:0.72rem;font-family:IBM Plex Mono,monospace;
                                    color:#555;margin-top:0.2rem'>
                            Current: {current_level.upper()} → Next: {next_level.upper() if next_level else "—"}
                        </div>
                    </div>
                    <div style='text-align:right'>
                        <div style='font-family:IBM Plex Mono,monospace;font-size:1.6rem;
                                    font-weight:800;color:{bar_color};line-height:1'>{percent}%</div>
                        <div style='font-size:0.62rem;color:#555;text-transform:uppercase;
                                    letter-spacing:0.1em'>Threshold: {threshold}%</div>
                    </div>
                </div>
                <div class="score-bar-track" style='margin-bottom:0.75rem'>
                    <div class="score-bar-fill" style='width:{percent}%;background:{bar_color}'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Checkboxes — one per checkpoint
            st.markdown(f"**✅ Milestone Checklist — {display_name.title()}** `({current_level})`")
            st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

            cols_per_row = 2
            cp_list = checkpoints
            for row_start in range(0, len(cp_list), cols_per_row):
                row_cps = cp_list[row_start:row_start + cols_per_row]
                cols    = st.columns(len(row_cps))
                for col, cp in zip(cols, row_cps):
                    with col:
                        cp_id    = cp["id"]
                        cp_label = cp["label"]
                        cp_wt    = cp["weight"]
                        current_val = checked.get(cp_id, False)
                        new_val = st.checkbox(
                            f"{cp_label}  *(+{cp_wt}%)*",
                            value=current_val,
                            key=f"chk_{skill_key}_{cp_id}"
                        )
                        if new_val != current_val:
                            st.session_state.progress_data[skill_key]["checked"][cp_id] = new_val
                            # Reset AI verdict when progress changes
                            st.session_state.progress_data[skill_key]["ai_verdict"] = None
                            st.rerun()

            st.markdown("")

            # Upgrade advice pill
            if upgrade_advice:
                st.markdown(f"""
                <div style='background:#4f9eff10;border:1px solid #4f9eff30;border-radius:8px;
                            padding:0.6rem 1rem;font-size:0.82rem;color:#4f9eff;margin-bottom:0.75rem'>
                    💡 <b>Upgrade Tip:</b> {upgrade_advice}
                </div>
                """, unsafe_allow_html=True)

            # AI Evaluation button + result
            btn_col, remove_col = st.columns([3, 1])
            with btn_col:
                eval_btn = st.button(
                    f"🤖 Get AI Recommendation for {display_name.title()}",
                    key=f"eval_{skill_key}"
                )
            with remove_col:
                remove_btn = st.button("🗑️ Remove", key=f"remove_{skill_key}")

            if remove_btn:
                del st.session_state.progress_data[skill_key]
                st.rerun()

            if eval_btn:
                completed = [cp["label"] for cp in checkpoints if checked.get(cp["id"], False)]
                pending   = [cp["label"] for cp in checkpoints if not checked.get(cp["id"], False)]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                with st.spinner(f"AI is evaluating your {display_name} progress..."):
                    verdict_data = get_ai_upgrade_recommendation(
                        display_name, current_level, completed, pending, percent, model
                    )
                st.session_state.progress_data[skill_key]["ai_verdict"] = verdict_data
                st.rerun()

            # Show AI verdict if available
            ai_v = skill_data.get("ai_verdict")
            if ai_v:
                verdict_str  = ai_v.get("verdict", "")
                confidence   = ai_v.get("confidence", 0)
                summary      = ai_v.get("summary", "")
                gaps         = ai_v.get("missing_gaps", [])
                actions      = ai_v.get("action_items", [])
                days_left    = ai_v.get("estimated_days_to_ready", 0)
                encouragement = ai_v.get("encouragement", "")

                if verdict_str == "ready_to_advance":
                    v_class = "verdict-ready"
                    v_icon  = "🚀"
                    v_text  = f"Ready to advance to {next_level.upper()}!"
                    v_color = "#00e5a0"
                elif verdict_str == "almost_there":
                    v_class = "verdict-almost"
                    v_icon  = "⚡"
                    v_text  = f"Almost there — ~{days_left} more days to go"
                    v_color = "#f5c542"
                else:
                    v_class = "verdict-notyet"
                    v_icon  = "📚"
                    v_text  = f"Keep going — complete more milestones first"
                    v_color = "#ff5e5e"

                st.markdown(f"""
                <div class="{v_class}">
                    <div style='font-size:0.62rem;letter-spacing:0.2em;text-transform:uppercase;
                                color:{v_color};font-family:IBM Plex Mono,monospace;margin-bottom:0.4rem'>
                        AI LEVEL-UP VERDICT · {confidence}% confidence
                    </div>
                    <div style='font-size:1.4rem;font-weight:800;color:{v_color};margin-bottom:0.4rem'>
                        {v_icon} {v_text}
                    </div>
                    <div style='font-size:0.85rem;color:#aaa'>{summary}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("")

                v1, v2 = st.columns(2)
                with v1:
                    if gaps:
                        st.markdown("**🔍 Gaps to Address**")
                        for g in gaps:
                            st.markdown(f'<div class="flag-card">{g}</div>', unsafe_allow_html=True)
                with v2:
                    if actions:
                        st.markdown("**📌 Action Items**")
                        for i, a in enumerate(actions, 1):
                            st.markdown(f"""
                            <div style='background:#111120;border-left:3px solid #4f9eff;
                                        border-radius:0 8px 8px 0;padding:0.5rem 0.75rem;
                                        margin-bottom:0.4rem;font-size:0.83rem'>
                                <span style='font-family:IBM Plex Mono,monospace;
                                             font-size:0.65rem;color:#4f9eff'>STEP {i}</span><br/>
                                {a}
                            </div>
                            """, unsafe_allow_html=True)

                if encouragement:
                    st.markdown(f"""
                    <div style='background:#111120;border:1px solid #6f3cff30;border-radius:8px;
                                padding:0.75rem 1rem;font-size:0.85rem;color:#a78bfa;
                                font-style:italic;margin-top:0.5rem'>
                        ✨ {encouragement}
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")


# ── Shared Inputs for Candidate / Recruiter modes ─────────────────────────────
if st.session_state.mode in ["candidate", "recruiter"]:
    col_l, col_r = st.columns([1, 1], gap="large")
    with col_l:
        label = "Upload Resume" if st.session_state.mode == "candidate" else "Upload Candidate Resume"
        st.markdown(f"### {label}")
        uploaded_file = st.file_uploader("PDF only", type=["pdf"], label_visibility="collapsed")
    with col_r:
        st.markdown("### Job Description")
        job_description = st.text_area("Paste JD", height=220,
                                       placeholder="Paste the full job description here...",
                                       label_visibility="collapsed")
    st.markdown("")

    if st.session_state.mode == "candidate":
        analyze_btn   = st.button("🔍  Analyze Resume")
        recruiter_btn = False
    else:
        analyze_btn   = False
        recruiter_btn = st.button("🏢  Run Recruiter Analysis")
else:
    analyze_btn   = False
    recruiter_btn = False
    uploaded_file = None
    job_description = ""


# ═══════════════════════════════════════════════════════════════════════════════
# CANDIDATE MODE
# ═══════════════════════════════════════════════════════════════════════════════

if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a resume PDF.")
        st.stop()
    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    data          = run_shared_pipeline(uploaded_file, job_description)
    resume_text   = data["resume_text"]
    jd_text       = data["jd_text"]
    sem_score     = data["sem_score"]
    ats_final     = data["ats_final"]
    kw_density    = data["kw_density"]
    resume_skills = data["resume_skills"]
    jd_skills     = data["jd_skills"]
    gemini_model  = data["gemini_model"]
    missing_skills = sorted(jd_skills - resume_skills)

    with st.expander("🐛 Debug — ATS internals", expanded=False):
        resume_words_debug = re.findall(r"\w+", resume_text.lower())
        jd_words_debug     = re.findall(r"\w+", jd_text.lower())
        resume_count_debug = Counter(resume_words_debug)
        jd_kw_debug   = {w for w in set(jd_words_debug) if len(w) > 2 and w not in _STOPWORDS and not w.isdigit()}
        matched_debug = {kw for kw in jd_kw_debug if resume_count_debug[kw] > 0}
        st.markdown(f"**JD keywords ({len(jd_kw_debug)}):** `{', '.join(sorted(jd_kw_debug))}`")
        st.markdown(f"**Matched ({len(matched_debug)}):** `{', '.join(sorted(matched_debug))}`")
        st.markdown(f"**Not matched ({len(jd_kw_debug - matched_debug)}):** `{', '.join(sorted(jd_kw_debug - matched_debug))}`")

    st.markdown("---")
    st.markdown("## Results")

    c1, c2, c3 = st.columns(3)
    with c1: score_card("Semantic Match", sem_score)
    with c2: score_card("ATS Score", ats_final)
    with c3: score_card("Keyword Density", kw_density)

    st.markdown("")

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("**✅ Resume Skills**")
        pills = "".join(f'<span class="pill pill-green">{s}</span>' for s in sorted(resume_skills))
        st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None detected</span>"}</div>', unsafe_allow_html=True)
    with s2:
        st.markdown("**🎯 JD Skills**")
        pills = "".join(f'<span class="pill pill-blue">{s}</span>' for s in sorted(jd_skills))
        st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None detected</span>"}</div>', unsafe_allow_html=True)
    with s3:
        st.markdown("**❌ Missing Skills**")
        if missing_skills:
            pills = "".join(f'<span class="pill pill-red">{s}</span>' for s in missing_skills)
            st.markdown(f'<div class="pill-container">{pills}</div>', unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#00e5a0;font-size:0.9rem;'>No missing skills 🎉</span>", unsafe_allow_html=True)

    if missing_skills:
        st.markdown("")
        st.markdown("---")
        st.markdown("## 🎓 YouTube Learning Roadmap")
        st.markdown("<p style='color:#555; margin-top:-0.5rem;'>Personalized 3-stage learning path for your skill gaps</p>", unsafe_allow_html=True)

        with st.spinner("Building your YouTube learning roadmap..."):
            roadmap = get_youtube_roadmap(missing_skills, gemini_model)

        if roadmap:
            for skill, d in roadmap.items():
                st.markdown(f"### 🛠️ {skill.title()}")
                why = d.get("why_important","")
                if why:
                    st.markdown(f"<p style='color:#888;font-size:0.85rem;margin-bottom:1rem'>💡 {why}</p>", unsafe_allow_html=True)
                tab1, tab2, tab3 = st.tabs(["🟢 Beginner", "🟡 Intermediate", "🔴 Expert"])
                with tab1:
                    for course in d.get("beginner", []): render_course_card(course, "beginner")
                with tab2:
                    for course in d.get("intermediate", []): render_course_card(course, "intermediate")
                with tab3:
                    for course in d.get("expert", []): render_course_card(course, "expert")
                st.markdown("")

    # Tip to use Progress Tracker
    if missing_skills:
        st.markdown(f"""
        <div style='background:#4f9eff10;border:1px solid #4f9eff30;border-radius:10px;
                    padding:0.85rem 1.1rem;margin-top:1rem;font-size:0.85rem'>
            💡 <b>Pro Tip:</b> Switch to <b>📊 Progress Tracker</b> mode in the sidebar to track
            your learning progress for <b>{", ".join(missing_skills[:3])}{"..." if len(missing_skills) > 3 else ""}</b>
            and get AI-powered level-up recommendations!
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🔩 Raw JSON"):
        st.json({"semantic_score": sem_score, "ats_score": ats_final, "keyword_density": kw_density,
                 "resume_skills": sorted(resume_skills), "jd_skills": sorted(jd_skills),
                 "missing_skills": missing_skills})


# ═══════════════════════════════════════════════════════════════════════════════
# RECRUITER MODE
# ═══════════════════════════════════════════════════════════════════════════════

if recruiter_btn:
    if not uploaded_file:
        st.error("Please upload a candidate resume PDF.")
        st.stop()
    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    st.markdown("""
    <div class="recruiter-banner">
        <span style='font-size:1.5rem'>🏢</span>
        <div>
            <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.3rem'>
                <span style='font-weight:700;font-size:1rem;color:#e8e4dc'>Recruiter Analysis Mode</span>
                <span class="recruiter-badge">ACTIVE</span>
            </div>
            <div style='font-size:0.82rem;color:#666'>Backend: Resume extraction → Rule engine → LLM analysis → Score computation → Dashboard</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Step 1 of 3 — Fetching structured resume data...**")
    data = run_shared_pipeline(uploaded_file, job_description)
    resume_text   = data["resume_text"]
    jd_text       = data["jd_text"]
    sem_score     = data["sem_score"]
    ats_final     = data["ats_final"]
    kw_density    = data["kw_density"]
    resume_skills = data["resume_skills"]
    jd_skills     = data["jd_skills"]
    gemini_model  = data["gemini_model"]

    st.markdown("**Step 2 of 3 — Running rule engine + LLM analysis...**")
    with st.spinner("Performing recruiter-grade analysis..."):
        report = run_recruiter_analysis(resume_text, jd_text, resume_skills, jd_skills, sem_score, ats_final, gemini_model)

    st.markdown("**Step 3 of 3 — Computing scores & storing results...**")
    if report:
        import time
        report["_timestamp"]      = time.strftime("%H:%M:%S")
        report["_resume_preview"] = resume_text[:120] + "..."
        st.session_state.recruiter_history.append(report)
        st.session_state.recruiter_report = report

    st.markdown("---")
    st.markdown("## 📊 Recruiter Dashboard")

    if report:
        verdict = report.get("verdict","")
        reason  = report.get("verdict_reason","")
        v_class = "verdict-hire" if "Hire" in verdict or "Strong" in verdict else \
                  ("verdict-maybe" if "Maybe" in verdict or "Good" in verdict else "verdict-reject")
        v_color = "#00e5a0" if "Hire" in verdict or "Strong" in verdict else \
                  ("#f5c542" if "Maybe" in verdict or "Good" in verdict else "#ff5e5e")
        v_icon  = "✅" if "Hire" in verdict or "Strong" in verdict else \
                  ("⚠️" if "Maybe" in verdict or "Good" in verdict else "❌")

        st.markdown(f"""
        <div class="{v_class}" style='margin-bottom:1.5rem'>
            <div style='font-size:0.68rem;letter-spacing:0.2em;text-transform:uppercase;color:{v_color};font-family:IBM Plex Mono,monospace;margin-bottom:0.5rem'>HIRING VERDICT</div>
            <div style='font-size:1.8rem;font-weight:800;color:{v_color};margin-bottom:0.5rem'>{v_icon} {verdict}</div>
            <div style='font-size:0.88rem;color:#aaa'>{reason}</div>
        </div>
        """, unsafe_allow_html=True)

        overall = report.get("overall_score", 0)
        o_color = "#00e5a0" if overall >= 75 else ("#f5c542" if overall >= 50 else "#ff5e5e")

        mc1, mc2 = st.columns([1, 2])
        with mc1:
            st.markdown(f"""
            <div class="metric-card" style='padding:2rem'>
                <div style='font-size:4rem;font-weight:800;font-family:IBM Plex Mono,monospace;color:{o_color};line-height:1'>{overall}</div>
                <div style='font-size:0.5rem;color:#555;font-family:IBM Plex Mono,monospace'>/100</div>
                <div style='font-size:0.68rem;letter-spacing:0.18em;text-transform:uppercase;color:#555;margin-top:0.5rem'>Overall Score</div>
                <div style='font-size:0.72rem;color:#555;margin-top:0.5rem'>Salary Band: <span style='color:#4f9eff'>{report.get("salary_band_fit","").upper()}</span></div>
            </div>
            """, unsafe_allow_html=True)
        with mc2:
            scores = report.get("scores", {})
            render_recruiter_score_bar("Skill Match",            scores.get("skill_match", 0))
            render_recruiter_score_bar("Experience Relevance",   scores.get("experience_relevance", 0))
            render_recruiter_score_bar("Communication Clarity",  scores.get("communication_clarity", 0))
            render_recruiter_score_bar("Technical Depth",        scores.get("technical_depth", 0))
            render_recruiter_score_bar("Culture Fit Indicators", scores.get("culture_fit_indicators", 0))

        st.markdown("")

        summary = report.get("candidate_summary","")
        if summary:
            st.markdown(f"""
            <div style='background:#111120;border-left:3px solid #6f3cff;border-radius:0 12px 12px 0;padding:1rem 1.25rem;margin-bottom:1.5rem'>
                <div style='font-size:0.65rem;letter-spacing:0.2em;color:#a78bfa;font-family:IBM Plex Mono,monospace;margin-bottom:0.5rem'>CANDIDATE SUMMARY</div>
                <div style='font-size:0.9rem;color:#e8e4dc;line-height:1.7'>{summary}</div>
            </div>
            """, unsafe_allow_html=True)

        col_s, col_f = st.columns(2)
        with col_s:
            st.markdown("**✅ Strengths**")
            for s in report.get("strengths", []):
                st.markdown(f'<div class="strength-card">{s}</div>', unsafe_allow_html=True)
        with col_f:
            st.markdown("**🚩 Red Flags**")
            flags = report.get("red_flags",[]) + report.get("_meta",{}).get("rule_flags",[])
            if flags:
                for f in flags:
                    st.markdown(f'<div class="flag-card">{f}</div>', unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#00e5a0;font-size:0.88rem'>No red flags detected ✅</span>", unsafe_allow_html=True)

        st.markdown("")
        st.markdown("### 🎯 Skill Match Breakdown")
        meta      = report.get("_meta",{})
        match_pct = meta.get("match_pct",0)
        skb       = report.get("skill_match_breakdown",{})
        st.markdown(f"""
        <div style='background:#111120;border:1px solid #1e1e2e;border-radius:12px;padding:1.25rem;margin-bottom:1rem'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem'>
                <span style='font-size:0.72rem;color:#555;letter-spacing:0.15em;text-transform:uppercase;font-family:IBM Plex Mono,monospace'>Skill Overlap</span>
                <span style='font-family:IBM Plex Mono,monospace;font-size:1.4rem;font-weight:800;color:{"#00e5a0" if match_pct >= 70 else ("#f5c542" if match_pct >= 40 else "#ff5e5e")}'>{match_pct}%</span>
            </div>
            <div style='background:#1e1e2e;border-radius:999px;height:8px;overflow:hidden'>
                <div style='width:{match_pct}%;height:100%;background:{"#00e5a0" if match_pct >= 70 else ("#f5c542" if match_pct >= 40 else "#ff5e5e")};border-radius:999px;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        sk1, sk2, sk3, sk4 = st.columns(4)
        with sk1:
            st.markdown("**✅ Matched**")
            pills = "".join(f'<span class="pill pill-green">{s}</span>' for s in skb.get("matched",[]))
            st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None</span>"}</div>', unsafe_allow_html=True)
        with sk2:
            st.markdown("**❗ Critical Missing**")
            pills = "".join(f'<span class="pill pill-red">{s}</span>' for s in skb.get("missing_critical",[]))
            st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None</span>"}</div>', unsafe_allow_html=True)
        with sk3:
            st.markdown("**⚠️ Nice-to-have**")
            pills = "".join(f'<span class="pill pill-yellow">{s}</span>' for s in skb.get("missing_nice_to_have",[]))
            st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None</span>"}</div>', unsafe_allow_html=True)
        with sk4:
            st.markdown("**⭐ Bonus Skills**")
            pills = "".join(f'<span class="pill pill-blue">{s}</span>' for s in skb.get("bonus_skills",[]))
            st.markdown(f'<div class="pill-container">{pills or "<span style=\'color:#444\'>None</span>"}</div>', unsafe_allow_html=True)

        st.markdown("")
        st.markdown("### 💬 Suggested Interview Questions")
        for i, iq in enumerate(report.get("interview_questions",[]), 1):
            st.markdown(f"""
            <div style='background:#111120;border:1px solid #1e1e2e;border-radius:10px;padding:1rem;margin-bottom:0.6rem'>
                <div style='font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#6f3cff;margin-bottom:0.4rem;letter-spacing:0.15em'>Q{i:02d}</div>
                <div style='font-size:0.9rem;color:#e8e4dc;margin-bottom:0.4rem'>{iq.get("question","")}</div>
                <div style='font-size:0.75rem;color:#555'>💡 {iq.get("reason","")}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        rec = report.get("hiring_recommendation","")
        if rec:
            st.markdown("### 📋 Hiring Recommendation")
            st.markdown(f"""
            <div style='background:#111120;border:1px solid #6f3cff30;border-radius:12px;padding:1.25rem'>
                <div style='font-size:0.92rem;color:#e8e4dc;line-height:1.7'>{rec}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown("### 📐 Base ATS Scores")
        bc1, bc2, bc3 = st.columns(3)
        with bc1: score_card("Semantic Match", sem_score)
        with bc2: score_card("ATS Score", ats_final)
        with bc3: score_card("Keyword Density", kw_density)
        st.markdown("")

        if len(st.session_state.recruiter_history) > 1:
            st.markdown("---")
            st.markdown("### 📋 Session History — Candidates Reviewed")
            for i, hist in enumerate(reversed(st.session_state.recruiter_history), 1):
                v     = hist.get("verdict","")
                score = hist.get("overall_score",0)
                ts    = hist.get("_timestamp","")
                v_col = "#00e5a0" if "Hire" in v or "Strong" in v else ("#f5c542" if "Maybe" in v or "Good" in v else "#ff5e5e")
                st.markdown(f"""
                <div class="history-card">
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div>
                            <div style='font-size:0.62rem;color:#555;font-family:IBM Plex Mono,monospace;margin-bottom:0.3rem'>{ts} · Candidate #{len(st.session_state.recruiter_history) - i + 1}</div>
                            <div style='font-size:0.78rem;color:#e8e4dc'>{hist.get("_resume_preview","")}</div>
                        </div>
                        <div style='text-align:right;min-width:100px'>
                            <div style='font-family:IBM Plex Mono,monospace;font-size:1.2rem;font-weight:800;color:{v_col}'>{score}</div>
                            <div style='font-size:0.62rem;color:{v_col}'>{v}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("🔩 Raw Recruiter Report JSON"):
            st.json(report)
    else:
        st.error("Recruiter analysis failed. Please try again.")