"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Timer, Play, Loader2, RotateCcw, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useResume } from "@/context";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Question {
  id: number;
  type: string;
  question: string;
  hint: string;
  difficulty: "easy" | "medium" | "hard";
}

interface Feedback {
  overall_score: number;
  communication_score: number;
  technical_score: number;
  confidence_score: number;
  verdict: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  per_question: { question_id: number; score: number; comment: string; ideal_answer_hint: string }[];
  next_steps: string[];
}

interface ChatMsg {
  text: string;
  isAI: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_PYTHON_API_URL || "http://localhost:8000";

const EXPERIENCE_OPTIONS = [
  "Entry Level (0-2 yrs)",
  "Mid Level (2-5 yrs)",
  "Senior Level (5-8 yrs)",
  "Lead / Principal (8+ yrs)",
];

const FOCUS_OPTIONS = [
  "Data Structures & Algorithms",
  "System Design",
  "Behavioral / Leadership",
  "Machine Learning",
  "Frontend Development",
  "Backend Development",
  "DevOps / Cloud",
  "Database Design",
];

function difficultyStyle(d: string) {
  if (d === "easy")   return "bg-success/10 text-success";
  if (d === "medium") return "bg-warning/10 text-warning";
  return "bg-destructive/10 text-destructive";
}

function scoreColor(v: number) {
  return v >= 70 ? "text-success" : v >= 40 ? "text-warning" : "text-destructive";
}
function scoreBarColor(v: number) {
  return v >= 70 ? "bg-success" : v >= 40 ? "bg-warning" : "bg-destructive";
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground font-medium">{label}</span>
        <span className={cn("font-mono font-bold", scoreColor(value))}>{value}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-700", scoreBarColor(value))}
          style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function ChatBubble({ msg }: { msg: ChatMsg }) {
  return (
    <div className={cn("flex", msg.isAI ? "justify-start" : "justify-end")}>
      <div className={cn(
        "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
        msg.isAI
          ? "rounded-tl-sm bg-secondary text-foreground"
          : "rounded-tr-sm bg-primary text-primary-foreground"
      )}>
        {msg.text}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type Stage = "setup" | "mock-intro" | "mock-active" | "mock-feedback";

export default function InterviewGuide() {
  // ── Setup state ────────────────────────────────────────────────────────────
  const { setInterviewResult } = useResume();
  const [role, setRole] = useState("");
  const [experience, setExperience] = useState(EXPERIENCE_OPTIONS[1]);
  const [focusAreas, setFocusAreas] = useState<string[]>([]);

  // ── Shared state ───────────────────────────────────────────────────────────
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [stage, setStage] = useState<Stage>("setup");

  // ── Chat state ─────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMsg[]>([
    { text: "Hi! I'm your AI Interview Coach. Enter a role above to generate tailored interview questions, or start a mock session.", isAI: true },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // ── Mock interview state ───────────────────────────────────────────────────
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [timer, setTimer] = useState(0);
  const [timerActive, setTimerActive] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loadingFeedback, setLoadingFeedback] = useState(false);

  // ── Active tab ─────────────────────────────────────────────────────────────
  const [tab, setTab] = useState<"coach" | "questions" | "mock">("coach");

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (timerActive) interval = setInterval(() => setTimer(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, [timerActive]);

  // ── Auto-scroll chat ───────────────────────────────────────────────────────
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  // ── Generate questions ─────────────────────────────────────────────────────
  const generateQuestions = async () => {
    if (!role.trim()) { toast.error("Please enter a job role first"); return; }
    setLoadingQuestions(true);
    try {
      const res = await fetch(`${API}/interview/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, experience, focus: focusAreas }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to generate questions");
      setQuestions(data.questions || []);
      setAnswers(new Array(data.questions.length).fill(""));
      toast.success(`${data.questions.length} questions generated!`);
      setTab("questions");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to generate questions");
    } finally {
      setLoadingQuestions(false);
    }
  };

  // ── Chat with coach — uses POST /chat/message ──────────────────────────────
  const sendChat = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatInput("");
    setMessages(m => [...m, { text: userMsg, isAI: false }]);
    setChatLoading(true);

    const updatedHistory: { role: "user" | "assistant"; text: string }[] = [
      ...chatHistory,
      { role: "user", text: userMsg },
    ];

    try {
      const res = await fetch(`${API}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          history: chatHistory.slice(-10), // last 10 turns for context
        }),
      });
      const data = await res.json();
      const reply = data.reply || "I couldn't generate a response. Please try again.";
      setMessages(m => [...m, { text: reply, isAI: true }]);
      setChatHistory([...updatedHistory, { role: "assistant", text: reply }]);
    } catch {
      setMessages(m => [...m, { text: "Sorry, I couldn't connect to the server. Please try again.", isAI: true }]);
    }
    setChatLoading(false);
  };

  // ── Mock interview ─────────────────────────────────────────────────────────
  const startMock = () => {
    if (questions.length === 0) { toast.error("Generate questions first"); setTab("questions"); return; }
    setCurrentQ(0);
    setCurrentAnswer("");
    setAnswers(new Array(questions.length).fill(""));
    setTimer(0);
    setTimerActive(true);
    setFeedback(null);
    setStage("mock-active");
    setTab("mock");
  };

  const submitAnswer = () => {
    const updated = [...answers];
    updated[currentQ] = currentAnswer.trim() || "[Skipped]";
    setAnswers(updated);
    setCurrentAnswer("");

    if (currentQ < questions.length - 1) {
      setCurrentQ(q => q + 1);
      setTimer(0);
    } else {
      // All answered — get feedback
      setTimerActive(false);
      setStage("mock-feedback");
      getFeedback(updated);
    }
  };

  const getFeedback = async (finalAnswers: string[]) => {
    setLoadingFeedback(true);
    try {
      const res = await fetch(`${API}/interview/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, questions, answers: finalAnswers }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to generate feedback");
      setFeedback(data);
      // ── Persist to context so /report can use it ──────────────────────────
      setInterviewResult({ role, questions, answers: finalAnswers, feedback: data });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to generate feedback");
    } finally {
      setLoadingFeedback(false);
    }
  };

  const resetMock = () => {
    setStage("mock-intro");
    setFeedback(null);
    setCurrentQ(0);
    setAnswers(new Array(questions.length).fill(""));
    setCurrentAnswer("");
    setTimer(0);
    setTimerActive(false);
  };

  const toggleFocus = (f: string) =>
    setFocusAreas(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5">

      {/* ── Setup bar ──────────────────────────────────────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5 space-y-4">
        <p className="text-sm font-semibold text-foreground">🎯 Interview Setup</p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground font-medium">Job Role</p>
            <Input
              placeholder="e.g. Senior Data Scientist"
              value={role}
              onChange={e => setRole(e.target.value)}
              onKeyDown={e => e.key === "Enter" && generateQuestions()}
              className="bg-secondary border-none focus-visible:ring-primary/50"
            />
          </div>
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground font-medium">Experience Level</p>
            <div className="flex flex-wrap gap-1.5">
              {EXPERIENCE_OPTIONS.map(opt => (
                <button key={opt} onClick={() => setExperience(opt)}
                  className={cn("rounded-lg px-2.5 py-1 text-xs font-medium border transition-all",
                    experience === opt
                      ? "border-primary/50 bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:border-primary/30")}>
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">Focus Areas (optional)</p>
          <div className="flex flex-wrap gap-1.5">
            {FOCUS_OPTIONS.map(f => (
              <button key={f} onClick={() => toggleFocus(f)}
                className={cn("rounded-lg px-2.5 py-1 text-xs font-medium border transition-all",
                  focusAreas.includes(f)
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/30")}>
                {f}
              </button>
            ))}
          </div>
        </div>

        <Button onClick={generateQuestions} disabled={loadingQuestions || !role.trim()} className="gap-2">
          {loadingQuestions
            ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating...</>
            : <><ChevronRight className="h-4 w-4" /> Generate Questions</>}
        </Button>
      </motion.div>

      {/* ── Tab bar ────────────────────────────────────────────────────────── */}
      <div className="flex gap-2">
        {(["coach", "questions", "mock"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={cn("rounded-xl px-4 py-2 text-sm font-semibold border capitalize transition-all",
              tab === t
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-primary/30")}>
            {t === "coach" ? "💬 Coach" : t === "questions" ? `📋 Questions${questions.length ? ` (${questions.length})` : ""}` : "🎤 Mock Interview"}
          </button>
        ))}
      </div>

      {/* ── Coach tab ──────────────────────────────────────────────────────── */}
      {tab === "coach" && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card flex flex-col" style={{ height: "60vh" }}>
          <div className="border-b border-border p-4">
            <h3 className="text-sm font-medium text-foreground">AI Interview Coach</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Ask anything about interview prep or practice answering questions</p>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m, i) => <ChatBubble key={i} msg={m} />)}
            {chatLoading && (
              <div className="flex items-center gap-1.5 px-3 py-2">
                {[0, 150, 300].map(d => (
                  <span key={d} className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce"
                    style={{ animationDelay: `${d}ms` }} />
                ))}
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>
          <div className="border-t border-border p-4">
            <div className="flex gap-2">
              <Input
                placeholder="Ask about interview prep..."
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !chatLoading && sendChat()}
                className="bg-secondary border-none"
              />
              <Button size="icon" onClick={sendChat} disabled={chatLoading || !chatInput.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      )}

      {/* ── Questions tab ──────────────────────────────────────────────────── */}
      {tab === "questions" && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="space-y-3">
          {questions.length === 0 ? (
            <div className="glass-card p-12 text-center space-y-3">
              <p className="text-muted-foreground text-sm">No questions yet — enter a role and click Generate Questions.</p>
            </div>
          ) : (
            <>
              {questions.map((q, i) => (
                <div key={q.id} className="glass-card p-4 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-muted-foreground">Q{String(i + 1).padStart(2, "0")}</span>
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium capitalize", difficultyStyle(q.difficulty))}>
                      {q.difficulty}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground capitalize">
                      {q.type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-sm text-foreground font-medium">{q.question}</p>
                  <p className="text-xs text-muted-foreground">💡 {q.hint}</p>
                </div>
              ))}
              <Button onClick={() => { setTab("mock"); startMock(); }} className="w-full gap-2">
                <Play className="h-4 w-4" /> Start Mock Interview with These Questions
              </Button>
            </>
          )}
        </motion.div>
      )}

      {/* ── Mock interview tab ─────────────────────────────────────────────── */}
      {tab === "mock" && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <AnimatePresence mode="wait">

            {/* No questions yet */}
            {questions.length === 0 && (
              <motion.div key="no-q" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="glass-card p-12 text-center space-y-4">
                <Play className="mx-auto h-12 w-12 text-primary/40" />
                <p className="text-sm text-muted-foreground">Generate questions first to start the mock interview.</p>
                <Button variant="outline" onClick={() => setTab("coach")}>Go to Questions</Button>
              </motion.div>
            )}

            {/* Intro */}
            {questions.length > 0 && stage !== "mock-active" && stage !== "mock-feedback" && (
              <motion.div key="intro" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="glass-card p-10 text-center space-y-5">
                <Play className="mx-auto h-12 w-12 text-primary" />
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Mock Interview Ready</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {questions.length} questions · Role: <strong>{role}</strong> · {experience}
                  </p>
                </div>
                <Button onClick={startMock} size="lg">Begin Session</Button>
              </motion.div>
            )}

            {/* Active question */}
            {stage === "mock-active" && questions[currentQ] && (
              <motion.div key={`q-${currentQ}`} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    Question {currentQ + 1} of {questions.length}
                  </span>
                  <div className="flex items-center gap-2 rounded-full bg-secondary px-3 py-1 text-sm text-foreground">
                    <Timer className="h-3.5 w-3.5" />
                    {Math.floor(timer / 60)}:{String(timer % 60).padStart(2, "0")}
                  </div>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${((currentQ + 1) / questions.length) * 100}%` }} />
                </div>

                <div className="glass-card p-6 space-y-3">
                  <div className="flex gap-2 flex-wrap">
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                      difficultyStyle(questions[currentQ].difficulty))}>
                      {questions[currentQ].difficulty}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground capitalize">
                      {questions[currentQ].type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-base font-medium text-foreground">{questions[currentQ].question}</p>
                  <p className="text-xs text-muted-foreground">💡 {questions[currentQ].hint}</p>
                </div>

                <Textarea
                  value={currentAnswer}
                  onChange={e => setCurrentAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className="bg-secondary border-none resize-none h-32 text-sm focus-visible:ring-primary/50"
                />

                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1"
                    onClick={() => {
                      const updated = [...answers];
                      updated[currentQ] = "[Skipped]";
                      setAnswers(updated);
                      setCurrentAnswer("");
                      if (currentQ < questions.length - 1) { setCurrentQ(q => q + 1); setTimer(0); }
                      else { setTimerActive(false); setStage("mock-feedback"); getFeedback(updated); }
                    }}>
                    Skip
                  </Button>
                  <Button className="flex-1" onClick={submitAnswer}>
                    {currentQ < questions.length - 1 ? "Next Question →" : "Finish & Get Feedback"}
                  </Button>
                </div>
              </motion.div>
            )}

            {/* Feedback */}
            {stage === "mock-feedback" && (
              <motion.div key="feedback" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="space-y-5">

                {loadingFeedback && (
                  <div className="glass-card p-16 text-center space-y-4">
                    <Loader2 className="mx-auto h-10 w-10 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Analyzing your performance...</p>
                  </div>
                )}

                {feedback && !loadingFeedback && (
                  <>
                    {/* Verdict */}
                    <div className={cn("glass-card p-6 text-center space-y-2 border-2",
                      feedback.overall_score >= 70 ? "border-success/30 bg-success/5"
                        : feedback.overall_score >= 50 ? "border-warning/30 bg-warning/5"
                        : "border-destructive/30 bg-destructive/5")}>
                      <p className="text-xs font-mono tracking-widest uppercase text-muted-foreground">Interview Verdict</p>
                      <p className={cn("text-2xl font-bold", scoreColor(feedback.overall_score))}>
                        {feedback.overall_score >= 70 ? "✅" : feedback.overall_score >= 50 ? "⚠️" : "❌"} {feedback.verdict}
                      </p>
                      <p className="text-sm text-muted-foreground">{feedback.summary}</p>
                    </div>

                    {/* Scores */}
                    <div className="glass-card p-5 space-y-4">
                      <p className="text-xs font-mono tracking-widest uppercase text-muted-foreground">📊 Performance Scores</p>
                      <ScoreBar label="Overall"       value={feedback.overall_score} />
                      <ScoreBar label="Communication" value={feedback.communication_score} />
                      <ScoreBar label="Technical"     value={feedback.technical_score} />
                      <ScoreBar label="Confidence"    value={feedback.confidence_score} />
                    </div>

                    {/* Strengths / Weaknesses */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-foreground">✅ Strengths</h3>
                        {feedback.strengths.map((s, i) => (
                          <div key={i} className="rounded-r-xl border-l-4 border-success bg-success/5 px-3 py-2 text-sm">{s}</div>
                        ))}
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-foreground">⚠️ Areas to Improve</h3>
                        {feedback.weaknesses.map((w, i) => (
                          <div key={i} className="rounded-r-xl border-l-4 border-warning bg-warning/5 px-3 py-2 text-sm">{w}</div>
                        ))}
                      </div>
                    </div>

                    {/* Per-question breakdown */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-foreground">📝 Question Breakdown</h3>
                      {feedback.per_question.map((pq, i) => (
                        <div key={i} className="glass-card p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <p className="text-xs font-mono text-muted-foreground">Q{String(pq.question_id).padStart(2, "0")}</p>
                            <span className={cn("text-sm font-bold font-mono", scoreColor(pq.score))}>{pq.score}/100</span>
                          </div>
                          <p className="text-xs font-medium text-foreground">{questions[i]?.question}</p>
                          <p className="text-xs text-muted-foreground">{pq.comment}</p>
                          <p className="text-xs text-blue-400">💡 Ideal: {pq.ideal_answer_hint}</p>
                        </div>
                      ))}
                    </div>

                    {/* Suggestions & Next steps */}
                    <div className="glass-card p-5 space-y-3">
                      <h3 className="text-sm font-semibold text-foreground">🎯 Suggestions</h3>
                      {feedback.suggestions.map((s, i) => (
                        <div key={i} className="flex gap-3 items-start">
                          <span className="text-xs font-mono font-bold text-primary shrink-0">{String(i + 1).padStart(2, "0")}</span>
                          <p className="text-sm text-foreground">{s}</p>
                        </div>
                      ))}
                    </div>

                    <div className="glass-card p-5 space-y-3">
                      <h3 className="text-sm font-semibold text-foreground">🚀 Next Steps</h3>
                      {feedback.next_steps.map((s, i) => (
                        <div key={i} className="rounded-r-xl border-l-2 border-primary bg-primary/5 px-3 py-2 text-sm">{s}</div>
                      ))}
                    </div>

                    <Button variant="outline" onClick={resetMock} className="w-full gap-2">
                      <RotateCcw className="h-4 w-4" /> Retake Interview
                    </Button>
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}