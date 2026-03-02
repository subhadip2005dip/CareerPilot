"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, CheckCircle, Loader2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useResume } from "@/context";
import Link from "next/link";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CandidateResult {
  warnings: string[];
  semantic_score: number;
  ats_score: number;
  keyword_density: number;
  resume_skills: string[];
  jd_skills: string[];
  missing_skills: string[];
  roadmap: Roadmap;
  debug: { jd_keywords: string[]; matched: string[]; not_matched: string[] };
}

interface RecruiterResult {
  warnings: string[];
  semantic_score: number;
  ats_score: number;
  keyword_density: number;
  resume_skills: string[];
  jd_skills: string[];
  report: RecruiterReport;
}

interface RecruiterReport {
  verdict: string;
  verdict_reason: string;
  overall_score: number;
  scores: Record<string, number>;
  candidate_summary: string;
  strengths: string[];
  red_flags: string[];
  skill_match_breakdown: {
    matched: string[];
    missing_critical: string[];
    missing_nice_to_have: string[];
    bonus_skills: string[];
  };
  interview_questions: { question: string; reason: string }[];
  hiring_recommendation: string;
  salary_band_fit: string;
  _meta: { sem_score: number; ats_score: number; match_pct: number; rule_flags: string[] };
}

interface Roadmap {
  overall: {
    total_days: number;
    total_weeks: number;
    hours_per_day: number;
    difficulty: string;
    summary: string;
    recommended_order: string[];
    quick_wins: string[];
  };
  skills: SkillRoadmap[];
}

interface SkillRoadmap {
  skill: string;
  why_important: string;
  priority: string;
  difficulty: string;
  time_estimate: { beginner_days: number; intermediate_days: number; expert_days: number; total_days: number; time_note: string };
  approach: { step: number; action: string; duration: string }[];
  phases: { phase: string; days: string; daily_focus: string; daily_goal: string; phase_outcome: string }[];
  milestones: string[];
  tips: { do: string[]; dont: string[] };
  courses: {
    beginner: CourseItem[];
    intermediate: CourseItem[];
    expert: CourseItem[];
  };
}

interface CourseItem {
  title: string;
  channel: string;
  search_query: string;
  duration: string;
  what_you_learn: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

type Mode = "candidate" | "recruiter";

function scoreColor(v: number) {
  return v >= 70 ? "text-success" : v >= 40 ? "text-warning" : "text-destructive";
}
function scoreBarColor(v: number) {
  return v >= 70 ? "bg-success" : v >= 40 ? "bg-warning" : "bg-destructive";
}
function verdictColor(verdict: string) {
  if (verdict.includes("Strong") || verdict.includes("Hire")) return { text: "text-success", bg: "bg-success/10", border: "border-success/30" };
  if (verdict.includes("Good") || verdict.includes("Maybe")) return { text: "text-warning", bg: "bg-warning/10", border: "border-warning/30" };
  return { text: "text-destructive", bg: "bg-destructive/10", border: "border-destructive/30" };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Pill({ label, variant }: { label: string; variant: "green" | "blue" | "red" | "yellow" | "purple" }) {
  const styles = {
    green:  "bg-success/10 border-success/30 text-success",
    blue:   "bg-blue-500/10 border-blue-500/30 text-blue-400",
    red:    "bg-destructive/10 border-destructive/30 text-destructive",
    yellow: "bg-warning/10 border-warning/30 text-warning",
    purple: "bg-purple-400/10 border-purple-400/30 text-purple-400",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-mono font-medium", styles[variant])}>
      {label}
    </span>
  );
}

function ScoreCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass-card p-5 text-center space-y-2">
      <div className={cn("text-4xl font-bold font-mono", scoreColor(value))}>{value}%</div>
      <div className="text-xs tracking-widest uppercase text-muted-foreground">{label}</div>
      <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-700", scoreBarColor(value))}
          style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function SkillCard({ title, skills, variant }: { title: string; skills: string[]; variant: "green" | "blue" | "red" | "yellow" | "purple" }) {
  return (
    <div className="glass-card p-4 space-y-3">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <div className="flex flex-wrap gap-1.5">
        {skills.length > 0
          ? skills.map(s => <Pill key={s} label={s} variant={variant} />)
          : <span className="text-xs text-muted-foreground">None</span>}
      </div>
    </div>
  );
}

// ─── Skill Roadmap Card ───────────────────────────────────────────────────────

function SkillRoadmapCard({ sk, idx }: { sk: SkillRoadmap; idx: number }) {
  const [activeTab, setActiveTab] = useState<"dayplan" | "approach" | "milestones" | "beginner" | "advanced">("dayplan");
  const te = sk.time_estimate || {} as SkillRoadmap["time_estimate"];

  const priorityColors: Record<string, string> = {
    critical: "text-destructive border-destructive/30 bg-destructive/10",
    high:     "text-warning border-warning/30 bg-warning/10",
    medium:   "text-blue-400 border-blue-400/30 bg-blue-400/10",
    low:      "text-muted-foreground border-border bg-secondary",
  };
  const difficultyColors: Record<string, string> = {
    easy:        "text-success border-success/30 bg-success/10",
    moderate:    "text-warning border-warning/30 bg-warning/10",
    hard:        "text-destructive border-destructive/30 bg-destructive/10",
    "very hard": "text-destructive border-destructive/30 bg-destructive/10",
  };

  const tabs = [
    { key: "dayplan"    as const, label: "📅 Day Plan" },
    { key: "approach"   as const, label: "🧭 Approach" },
    { key: "milestones" as const, label: "🏁 Milestones" },
    { key: "beginner"   as const, label: "🟢 Beginner" },
    { key: "advanced"   as const, label: "🟡🔴 Advanced" },
  ];

  const phaseStyles: Record<string, { border: string; color: string; icon: string }> = {
    beginner:     { border: "border-l-success",     color: "text-success",     icon: "🟢" },
    intermediate: { border: "border-l-warning",     color: "text-warning",     icon: "🟡" },
    expert:       { border: "border-l-destructive", color: "text-destructive", icon: "🔴" },
  };

  const CourseCard = ({ c, stage }: { c: CourseItem; stage: string }) => {
    const stageColors: Record<string, string> = { beginner: "text-success", intermediate: "text-warning", expert: "text-destructive" };
    const ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(c.search_query || "")}`;
    return (
      <div className="rounded-xl border border-border/50 bg-secondary/40 p-4 space-y-2 hover:border-primary/30 transition-colors">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold text-foreground">{c.title}</p>
          <span className={cn("text-xs font-mono border rounded-full px-2 py-0.5 shrink-0", stageColors[stage],
            stage === "beginner" ? "border-success/30 bg-success/10" : stage === "intermediate" ? "border-warning/30 bg-warning/10" : "border-destructive/30 bg-destructive/10")}>
            {stage.toUpperCase()}
          </span>
        </div>
        <p className="text-xs text-blue-400 font-mono">📺 {c.channel}</p>
        <p className="text-xs text-muted-foreground">{c.what_you_learn}</p>
        <div className="flex items-center gap-4">
          <span className="text-xs text-muted-foreground">⏱ {c.duration}</span>
          <a href={ytUrl} target="_blank" rel="noreferrer"
            className="flex items-center gap-1 text-xs text-red-400 hover:underline font-mono">
            🔴 Search on YouTube <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    );
  };

  return (
    <div className="glass-card p-5 space-y-4">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <p className="text-base font-bold text-foreground">
            🛠️ {sk.skill.charAt(0).toUpperCase() + sk.skill.slice(1)}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{sk.why_important}</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn("text-xs font-mono border rounded-full px-2 py-0.5 uppercase", priorityColors[sk.priority] || priorityColors.low)}>
            {sk.priority}
          </span>
          <span className={cn("text-xs font-mono border rounded-full px-2 py-0.5", difficultyColors[sk.difficulty?.toLowerCase()] || difficultyColors.moderate)}>
            {sk.difficulty}
          </span>
          <span className="text-sm font-bold font-mono text-success">≈ {te.total_days || "?"} days</span>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs font-mono text-muted-foreground mb-1">
          <span>🟢 Beginner ({te.beginner_days || 0}d)</span>
          <span>🟡 Intermediate ({te.intermediate_days || 0}d)</span>
          <span>🔴 Expert ({te.expert_days || 0}d)</span>
        </div>
        <div className="flex h-2.5 rounded-full overflow-hidden gap-0.5">
          <div className="bg-success rounded-full" style={{ flex: te.beginner_days || 1 }} />
          <div className="bg-warning rounded-full" style={{ flex: te.intermediate_days || 1 }} />
          <div className="bg-destructive rounded-full" style={{ flex: te.expert_days || 1 }} />
        </div>
        <p className="text-xs text-muted-foreground font-mono mt-1">{te.time_note}</p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={cn("rounded-lg px-2.5 py-1 text-xs font-semibold border transition-all",
              activeTab === t.key
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-primary/30")}>
            {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={activeTab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>

          {activeTab === "dayplan" && (
            <div className="space-y-2">
              {(sk.phases || []).map(ph => {
                const ps = phaseStyles[ph.phase] || phaseStyles.beginner;
                return (
                  <div key={ph.phase} className={cn("rounded-xl border-l-4 bg-secondary/40 p-3 space-y-1", ps.border)}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold">{ps.icon} {ph.days}</span>
                      <span className="text-xs font-mono text-muted-foreground uppercase">{ph.phase}</span>
                    </div>
                    <p className="text-xs"><span className="font-semibold">Focus:</span> {ph.daily_focus}</p>
                    <p className="text-xs text-muted-foreground">🎯 <span className="font-semibold">Daily goal:</span> {ph.daily_goal}</p>
                    <p className={cn("text-xs", ps.color)}>✅ <span className="font-semibold">By end:</span> {ph.phase_outcome}</p>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === "approach" && (
            <div className="space-y-2">
              {(sk.approach || []).map(s => (
                <div key={s.step} className="flex gap-3 items-start rounded-xl bg-secondary/40 p-3">
                  <span className="text-xs font-mono text-primary font-bold shrink-0 pt-0.5">STEP {s.step}</span>
                  <div>
                    <p className="text-sm font-semibold">{s.action}</p>
                    <p className="text-xs font-mono text-blue-400 mt-0.5">⏱ {s.duration}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "milestones" && (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">🏁 MILESTONES</p>
                <div className="flex flex-wrap gap-1.5">
                  {(sk.milestones || []).map((m, i) => (
                    <span key={i} className="text-xs font-mono bg-success/10 border border-success/30 text-success rounded-full px-2.5 py-0.5">
                      ✓ {m}
                    </span>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">✅ DO THIS</p>
                  {(sk.tips?.do || []).map((d, i) => (
                    <div key={i} className="rounded-r-xl border-l-2 border-success bg-success/5 px-3 py-2 text-xs mb-2">{d}</div>
                  ))}
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">❌ AVOID</p>
                  {(sk.tips?.dont || []).map((d, i) => (
                    <div key={i} className="rounded-r-xl border-l-2 border-destructive bg-destructive/5 px-3 py-2 text-xs mb-2">{d}</div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "beginner" && (
            <div className="space-y-2">
              {(sk.courses?.beginner || []).length > 0
                ? sk.courses.beginner.map((c, i) => <CourseCard key={i} c={c} stage="beginner" />)
                : <p className="text-xs text-muted-foreground">No beginner courses.</p>}
            </div>
          )}

          {activeTab === "advanced" && (
            <div className="space-y-3">
              {(sk.courses?.intermediate || []).length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-warning">🟡 Intermediate</p>
                  {sk.courses.intermediate.map((c, i) => <CourseCard key={i} c={c} stage="intermediate" />)}
                </div>
              )}
              {(sk.courses?.expert || []).length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-destructive">🔴 Expert</p>
                  {sk.courses.expert.map((c, i) => <CourseCard key={i} c={c} stage="expert" />)}
                </div>
              )}
              {!sk.courses?.intermediate?.length && !sk.courses?.expert?.length &&
                <p className="text-xs text-muted-foreground">No advanced courses.</p>}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ResumeAnalyzerPage() {
  // ── Pull resume file + JD from context (set during /upload) ─────────────
  const { resumeFile, jobDescription: contextJd } = useResume();

  const [mode, setMode] = useState<Mode>("candidate");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [candidateResult, setCandidateResult] = useState<CandidateResult | null>(null);
  const [recruiterResult, setRecruiterResult] = useState<RecruiterResult | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Pre-fill JD from context (upload page stored it), or fall back to DB
  useEffect(() => {
    if (contextJd) {
      setJd(contextJd);
      return;
    }
    // Context is empty (e.g. page refresh) — load JD and full analysis from DB
    fetch("/api/resume/latest")
      .then(r => r.json())
      .then(data => {
        if (data.resume?.jobDescription) setJd(data.resume.jobDescription);
        // Restore the full candidate result (including roadmap) from the saved analysis blob
        if (data.resume?.analysis) {
          const saved = data.resume.analysis as CandidateResult;
          if (saved.roadmap || saved.semantic_score !== undefined) {
            setCandidateResult(saved);
          }
        }
      })
      .catch(() => {});
  }, [contextJd]);

  const runAnalysis = async () => {
    if (!resumeFile) { toast.error("No resume found — please upload one on the Upload page"); return; }
    if (!jd.trim()) { toast.error("Please paste a job description"); return; }

    setLoading(true);
    setCandidateResult(null);
    setRecruiterResult(null);
    setStatus(mode === "candidate" ? "🧠 Building semantic index and extracting skills..." : "🏢 Running recruiter-grade AI analysis...");

    const form = new FormData();
    form.append("resume", resumeFile);
    form.append("job_description", jd);

    // candidate → /api/resume/analyze (saves to DB)
    // recruiter → Python directly (no DB save needed for recruiter view)
    const endpoint = mode === "candidate"
      ? "/api/resume/analyze"
      : `${process.env.NEXT_PUBLIC_PYTHON_API_URL || "http://localhost:8000"}/ats/recruiter`;

    try {
      const res = await fetch(endpoint, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || "Analysis failed");

      if (mode === "candidate") setCandidateResult(data as CandidateResult);
      else setRecruiterResult(data as RecruiterResult);

      setStatus("");
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Analysis failed");
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  const result = candidateResult || recruiterResult;

  // ── No resume yet — prompt upload ─────────────────────────────────────────
  if (!resumeFile) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card flex flex-col items-center justify-center gap-5 p-16 text-center"
      >
        <div className="rounded-2xl bg-primary/10 p-5">
          <FileText className="h-10 w-10 text-primary" />
        </div>
        <div className="space-y-1.5">
          <h3 className="text-lg font-semibold text-foreground">No resume uploaded yet</h3>
          <p className="text-sm text-muted-foreground max-w-xs">
            Upload your resume once and it will be used for all analyses across the dashboard.
          </p>
        </div>
        <Link href="/upload">
          <Button size="lg" className="gap-2">
            <FileText className="h-4 w-4" /> Upload Resume
          </Button>
        </Link>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">

      {/* ── Mode toggle (label on right removed) ────────────────────────── */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => { setMode("candidate"); setCandidateResult(null); setRecruiterResult(null); }}
          className={cn("rounded-xl px-4 py-2 text-sm font-semibold border transition-all",
            mode === "candidate"
              ? "border-primary/50 bg-primary/10 text-primary"
              : "border-border text-muted-foreground hover:border-primary/30")}>
          👤 Candidate Mode
        </button>
        <button
          onClick={() => { setMode("recruiter"); setCandidateResult(null); setRecruiterResult(null); }}
          className={cn("rounded-xl px-4 py-2 text-sm font-semibold border transition-all",
            mode === "recruiter"
              ? "border-purple-400/50 bg-purple-400/10 text-purple-400"
              : "border-border text-muted-foreground hover:border-purple-400/30")}>
          🏢 Recruiter Mode
        </button>

        {/* Resume pill — shows which file is loaded from /upload */}
        <div className="ml-auto flex items-center gap-2 rounded-xl border border-success/30 bg-success/5 px-3 py-1.5">
          <CheckCircle className="h-3.5 w-3.5 text-success shrink-0" />
          <span className="text-xs font-medium text-success truncate max-w-[200px]">{resumeFile.name}</span>
        </div>
      </div>

      {/* ── Job description only ─────────────────────────────────────────── */}
      <div className="space-y-2">
        <p className="text-sm font-semibold text-foreground">📋 Job Description</p>
        <Textarea
          value={jd}
          onChange={e => setJd(e.target.value)}
          placeholder="Paste the full job description here..."
          className="bg-secondary border-none resize-none h-48 text-sm font-mono focus-visible:ring-primary/50"
        />
      </div>

      {/* ── Analyze button ───────────────────────────────────────────────── */}
      <Button
        className={cn("w-full gap-2 text-base", mode === "recruiter" && "bg-purple-500 hover:bg-purple-600")}
        onClick={runAnalysis}
        disabled={loading}
      >
        {loading
          ? <><Loader2 className="h-4 w-4 animate-spin" /> {status || "Analyzing..."}</>
          : mode === "candidate" ? "🔍 Analyze Resume" : "🏢 Run Recruiter Analysis"}
      </Button>

      {/* ── RESULTS ─────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {result && (
          <motion.div ref={resultsRef} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="space-y-6 pt-2">

            {(result.warnings || []).map((w, i) => (
              <div key={i} className="rounded-xl border border-warning/30 bg-warning/5 px-4 py-2.5 text-sm text-warning">
                ⚠️ {w}
              </div>
            ))}

            <div className="border-t border-border" />

            {/* ── CANDIDATE RESULTS ──────────────────────────────────────── */}
            {candidateResult && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-foreground">📊 Results</h2>

                <div className="grid gap-4 grid-cols-3">
                  <ScoreCard label="Semantic Match" value={candidateResult.semantic_score} />
                  <ScoreCard label="ATS Score"      value={candidateResult.ats_score} />
                  <ScoreCard label="Keyword Density" value={candidateResult.keyword_density} />
                </div>

                <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
                  <SkillCard title="✅ Resume Skills"  skills={candidateResult.resume_skills}  variant="green" />
                  <SkillCard title="🎯 JD Skills"      skills={candidateResult.jd_skills}      variant="blue" />
                  <div className="glass-card p-4 space-y-3">
                    <h4 className="text-sm font-semibold text-foreground">❌ Missing Skills</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {candidateResult.missing_skills.length > 0
                        ? candidateResult.missing_skills.map(s => <Pill key={s} label={s} variant="red" />)
                        : <span className="text-sm text-success font-medium">No missing skills 🎉</span>}
                    </div>
                  </div>
                </div>

                {/* Roadmap */}
                {candidateResult.roadmap?.skills?.length > 0 && (
                  <div className="space-y-5">
                    <div className="border-t border-border pt-4" />
                    <div>
                      <h2 className="text-lg font-bold text-foreground">🗓️ Personalized Learning Roadmap</h2>
                      <p className="text-sm text-muted-foreground mt-1">Day-by-day plan with milestones & YouTube courses — tailored to your background</p>
                    </div>

                    {candidateResult.roadmap.overall && (() => {
                      const ov = candidateResult.roadmap.overall;
                      return (
                        <div className="rounded-xl border border-success/20 bg-success/5 p-5 space-y-4">
                          <p className="text-xs font-mono tracking-widest uppercase text-success">📅 COMPLETE LEARNING ROADMAP</p>
                          <div className="flex gap-8 flex-wrap">
                            {[
                              { val: ov.total_days,          lbl: "Total Days",  color: "text-success" },
                              { val: ov.total_weeks,         lbl: "Weeks",       color: "text-warning" },
                              { val: `${ov.hours_per_day}h`, lbl: "Per Day",     color: "text-blue-400" },
                              { val: ov.difficulty,          lbl: "Difficulty",  color: "text-orange-400" },
                            ].map(({ val, lbl, color }) => (
                              <div key={lbl}>
                                <div className={cn("text-3xl font-bold font-mono", color)}>{val}</div>
                                <div className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">{lbl}</div>
                              </div>
                            ))}
                          </div>
                          {ov.summary && <p className="text-sm text-muted-foreground italic">💡 {ov.summary}</p>}
                          {ov.recommended_order?.length > 0 && (
                            <div>
                              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Order: </span>
                              <span className="text-xs text-foreground">{ov.recommended_order.join(" → ")}</span>
                            </div>
                          )}
                          {ov.quick_wins?.length > 0 && (
                            <div>
                              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Quick Wins: </span>
                              <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {ov.quick_wins.map(s => <Pill key={s} label={`⚡ ${s}`} variant="green" />)}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {candidateResult.roadmap.skills.map((sk, idx) => (
                      <SkillRoadmapCard key={idx} sk={sk} idx={idx} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── RECRUITER RESULTS ──────────────────────────────────────── */}
            {recruiterResult && (() => {
              const r = recruiterResult.report;
              const vc = verdictColor(r.verdict);
              const os = r.overall_score;
              const scoreLabels: Record<string, string> = {
                skill_match:            "Skill Match",
                experience_relevance:   "Experience Relevance",
                communication_clarity:  "Communication Clarity",
                technical_depth:        "Technical Depth",
                culture_fit_indicators: "Culture Fit",
              };
              return (
                <div className="space-y-6">
                  <h2 className="text-lg font-bold text-foreground">📊 Recruiter Dashboard</h2>

                  <div className={cn("rounded-xl border-2 p-6 text-center", vc.bg, vc.border)}>
                    <p className={cn("text-xs font-mono tracking-widest uppercase mb-2", vc.text)}>HIRING VERDICT</p>
                    <p className={cn("text-2xl font-bold", vc.text)}>
                      {r.verdict.includes("Strong") || r.verdict.includes("Hire") ? "✅" : r.verdict.includes("Good") || r.verdict.includes("Maybe") ? "⚠️" : "❌"} {r.verdict}
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">{r.verdict_reason}</p>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-[180px_1fr]">
                    <div className="glass-card p-5 text-center space-y-2">
                      <div className={cn("text-5xl font-bold font-mono", scoreColor(os))}>{os}</div>
                      <div className="text-xs text-muted-foreground font-mono">/100</div>
                      <div className="text-xs tracking-widest uppercase text-muted-foreground">Overall Score</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Salary Band: <span className="text-blue-400">{r.salary_band_fit?.toUpperCase()}</span>
                      </div>
                    </div>
                    <div className="glass-card p-5 space-y-3">
                      {Object.entries(scoreLabels).map(([k, lbl]) => {
                        const v = r.scores?.[k] || 0;
                        return (
                          <div key={k}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-muted-foreground">{lbl}</span>
                              <span className={cn("font-mono font-bold", scoreColor(v))}>{v}/100</span>
                            </div>
                            <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                              <div className={cn("h-full rounded-full transition-all duration-700", scoreBarColor(v))} style={{ width: `${v}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="glass-card border-l-4 border-l-purple-400 p-4">
                    <p className="text-xs font-mono tracking-widest uppercase text-purple-400 mb-2">CANDIDATE SUMMARY</p>
                    <p className="text-sm leading-relaxed text-foreground">{r.candidate_summary}</p>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">✅ Strengths</h3>
                      {(r.strengths || []).map((s, i) => (
                        <div key={i} className="rounded-r-xl border-l-4 border-success bg-success/5 px-3 py-2 text-sm">{s}</div>
                      ))}
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">🚩 Red Flags</h3>
                      {[...(r.red_flags || []), ...(r._meta?.rule_flags || [])].length > 0
                        ? [...(r.red_flags || []), ...(r._meta?.rule_flags || [])].map((f, i) => (
                          <div key={i} className="rounded-r-xl border-l-4 border-destructive bg-destructive/5 px-3 py-2 text-sm">{f}</div>
                        ))
                        : <p className="text-sm text-success">No red flags detected ✅</p>}
                    </div>
                  </div>

                  <div className="glass-card p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-mono tracking-widest uppercase text-muted-foreground">Skill Overlap</p>
                      <span className={cn("text-2xl font-bold font-mono", scoreColor(r._meta?.match_pct || 0))}>
                        {r._meta?.match_pct || 0}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden">
                      <div className={cn("h-full rounded-full transition-all duration-700", scoreBarColor(r._meta?.match_pct || 0))}
                        style={{ width: `${r._meta?.match_pct || 0}%` }} />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                      { label: "✅ Matched",          skills: r.skill_match_breakdown?.matched,              v: "green"  as const },
                      { label: "❗ Critical Missing", skills: r.skill_match_breakdown?.missing_critical,     v: "red"    as const },
                      { label: "⚠️ Nice-to-have",    skills: r.skill_match_breakdown?.missing_nice_to_have, v: "yellow" as const },
                      { label: "⭐ Bonus Skills",     skills: r.skill_match_breakdown?.bonus_skills,         v: "blue"   as const },
                    ].map(({ label, skills, v }) => (
                      <div key={label} className="space-y-2">
                        <p className="text-xs font-semibold text-muted-foreground">{label}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(skills || []).length > 0
                            ? (skills || []).map(s => <Pill key={s} label={s} variant={v} />)
                            : <span className="text-xs text-muted-foreground">None</span>}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">📐 Base ATS Scores</h3>
                    <div className="grid gap-4 grid-cols-3">
                      <ScoreCard label="Semantic Match"  value={recruiterResult.semantic_score} />
                      <ScoreCard label="ATS Score"       value={recruiterResult.ats_score} />
                      <ScoreCard label="Keyword Density" value={recruiterResult.keyword_density} />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-foreground">💬 Suggested Interview Questions</h3>
                    {(r.interview_questions || []).map((q, i) => (
                      <div key={i} className="glass-card p-4 space-y-1.5">
                        <p className="text-xs font-mono text-purple-400 tracking-widest">Q{String(i + 1).padStart(2, "0")}</p>
                        <p className="text-sm font-medium text-foreground">{q.question}</p>
                        <p className="text-xs text-muted-foreground">💡 {q.reason}</p>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground">📋 Hiring Recommendation</h3>
                    <div className="glass-card border border-purple-400/20 p-4 text-sm leading-relaxed text-foreground">
                      {r.hiring_recommendation}
                    </div>
                  </div>
                </div>
              );
            })()}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}