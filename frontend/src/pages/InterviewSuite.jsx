import React, { useEffect, useState } from "react";
import useSWR from "swr";
import {
  Bot,
  CheckCircle2,
  ClipboardCheck,
  Cpu,
  Mic,
  Play,
  Radio,
  Sparkles,
  UserCog,
  Video,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

/* ============================================================
   TASK 8 — Consolidated AI Interview Suite (4 modes)
   ============================================================ */

const MODES = [
  {
    id: "screening",
    label: "AI Screening",
    icon: ClipboardCheck,
    tagline: "8-dimension structured rubric",
    detail:
      "Short async screen. AI scores 8 dimensions with weights, then bands the candidate.",
    inputs: [
      { key: "focus_areas", label: "Focus areas", placeholder: "e.g. Apex depth, org scaling" },
    ],
    action: "Run rubric",
  },
  {
    id: "voice",
    label: "AI Voice",
    icon: Mic,
    tagline: "Live AI-led phone screen",
    detail:
      "AI conducts a 12-minute conversational screen — parses tone, hesitation, technical grounding.",
    inputs: [
      { key: "focus_areas", label: "Topics to probe", placeholder: "Kafka throughput, org design" },
    ],
    action: "Start voice interview",
  },
  {
    id: "copilot",
    label: "AI Copilot",
    icon: UserCog,
    tagline: "Live human interview copilot",
    detail:
      "Human interviewer leads. AI listens, surfaces follow-ups, flags red-herrings, drafts a scorecard in real time.",
    inputs: [
      { key: "interviewer", label: "Interviewer", placeholder: "Priya Menon (Engineering)" },
    ],
    action: "Enter interview room",
  },
  {
    id: "video",
    label: "Autonomous Video",
    icon: Video,
    tagline: "Fully AI-driven async video",
    detail:
      "Candidate answers 5 timed video questions. AI parses content, delivery, and integrity signals — recruiter reviews at the end.",
    inputs: [
      { key: "question_bank", label: "Question bank", placeholder: "engineering_l4_pack" },
    ],
    action: "Launch async video",
  },
];

export default function InterviewSuite() {
  const { data: cands } = useSWR("/world/candidates", fetcher);
  const [candId, setCandId] = useState(null);
  const [mode, setMode] = useState("screening");
  const [inputs, setInputs] = useState({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [phase, setPhase] = useState(null); // null | "warming" | "listening" | "scoring" | "done"

  useEffect(() => {
    if (cands && !candId) setCandId(cands[0]?.candidate_id);
  }, [cands, candId]);

  useEffect(() => {
    setResult(null);
    setPhase(null);
  }, [mode, candId]);

  const activeMode = MODES.find((m) => m.id === mode);
  const candidate = cands?.find((c) => c.candidate_id === candId);

  const run = async () => {
    if (!candId) return;
    setLoading(true);
    setResult(null);
    setPhase("warming");
    try {
      // The AI Screening mode calls the real 8-dim rubric endpoint.
      // The 3 other modes simulate the flow with paced phase transitions and
      // context-specific reports so executives see mode-appropriate depth.
      if (mode === "screening") {
        await new Promise((r) => setTimeout(r, 700));
        setPhase("scoring");
        const { data } = await api.post("/screening/rubric", {
          candidate_id: candId,
          notes: inputs.focus_areas || "",
        });
        setResult({ kind: "screening", data });
      } else if (mode === "voice") {
        setPhase("warming"); await new Promise((r) => setTimeout(r, 900));
        setPhase("listening"); await new Promise((r) => setTimeout(r, 2200));
        setPhase("scoring"); await new Promise((r) => setTimeout(r, 900));
        setResult({ kind: "voice", data: buildVoiceReport(candidate, inputs) });
      } else if (mode === "copilot") {
        setPhase("listening"); await new Promise((r) => setTimeout(r, 1600));
        setPhase("scoring"); await new Promise((r) => setTimeout(r, 900));
        setResult({ kind: "copilot", data: buildCopilotReport(candidate, inputs) });
      } else if (mode === "video") {
        setPhase("warming"); await new Promise((r) => setTimeout(r, 700));
        setPhase("listening"); await new Promise((r) => setTimeout(r, 2400));
        setPhase("scoring"); await new Promise((r) => setTimeout(r, 800));
        setResult({ kind: "video", data: buildVideoReport(candidate, inputs) });
      }
      setPhase("done");
    } catch (e) {
      setResult({ kind: "error", data: { error: String(e) } });
      setPhase("done");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div
        data-testid="interview-suite-root"
        className="p-6 space-y-6"
      >
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
            AI INTERVIEW SUITE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            One suite, four ways to screen.
          </h1>
          <div className="text-slate-500 text-sm">
            Pick the modality — from structured async screens to fully autonomous
            video — and get a context-specific report your hiring managers can act on.
          </div>
        </div>

        {/* Mode selector */}
        <div
          data-testid="interview-mode-selector"
          className="grid grid-cols-2 md:grid-cols-4 gap-2"
        >
          {MODES.map((m) => {
            const Icon = m.icon;
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                data-testid={`interview-mode-${m.id}`}
                onClick={() => setMode(m.id)}
                className={`text-left p-3 rounded-md border transition ${
                  active
                    ? "border-indigo-500/60 bg-indigo-500/10"
                    : "border-slate-800 bg-slate-900 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon
                    className={`w-4 h-4 ${active ? "text-indigo-300" : "text-slate-500"}`}
                    strokeWidth={1.5}
                  />
                  <div
                    className={`font-mono2 text-[10px] tracking-widest ${
                      active ? "text-indigo-300" : "text-slate-500"
                    }`}
                  >
                    {active ? "SELECTED" : "MODE"}
                  </div>
                </div>
                <div className="text-slate-100 text-[13px] font-semibold">
                  {m.label}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {m.tagline}
                </div>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4">
          {/* Config panel */}
          <div className="border border-slate-800 bg-slate-900 rounded-md p-4 space-y-3">
            <div>
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                MODE
              </div>
              <div className="text-slate-100 text-[13px] font-medium">
                {activeMode.label}
              </div>
              <div className="text-[11px] text-slate-400">
                {activeMode.detail}
              </div>
            </div>

            <div>
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                CANDIDATE
              </div>
              <select
                data-testid="interview-cand-select"
                value={candId || ""}
                onChange={(e) => setCandId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100"
              >
                {cands?.slice(0, 120).map((c) => (
                  <option key={c.candidate_id} value={c.candidate_id}>
                    {c.full_name} · {c.current_title}
                  </option>
                ))}
              </select>
            </div>

            {activeMode.inputs.map((i) => (
              <div key={i.key}>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                  {i.label.toUpperCase()}
                </div>
                <input
                  data-testid={`interview-input-${i.key}`}
                  value={inputs[i.key] || ""}
                  onChange={(e) =>
                    setInputs((prev) => ({ ...prev, [i.key]: e.target.value }))
                  }
                  placeholder={i.placeholder}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] text-slate-100 focus:outline-none focus:border-indigo-500/60"
                />
              </div>
            ))}

            <button
              data-testid="interview-run-btn"
              onClick={run}
              disabled={loading || !candId}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
            >
              <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
              {loading ? "RUNNING…" : activeMode.action.toUpperCase()}
            </button>
          </div>

          {/* Result panel */}
          <div className="border border-slate-800 bg-slate-900 rounded-md min-h-[420px]">
            {!result && !loading && (
              <div className="p-8 text-center text-slate-500 text-[12.5px]">
                Select a candidate, add optional context, and run the mode.
                Reports adapt per mode — rubric for screening, transcript-derived
                signal for voice, live-scoring for copilot, integrity + delivery
                for autonomous video.
              </div>
            )}
            {loading && <PhaseTicker phase={phase} mode={activeMode} />}
            {result?.kind === "screening" && <ScreeningReport data={result.data} />}
            {result?.kind === "voice"     && <VoiceReport     data={result.data} />}
            {result?.kind === "copilot"   && <CopilotReport   data={result.data} />}
            {result?.kind === "video"     && <VideoReport     data={result.data} />}
            {result?.kind === "error" && (
              <div className="p-6 text-rose-300 text-[13px]">
                {result.data.error}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

/* ------------------------------ */

function PhaseTicker({ phase, mode }) {
  const phases = {
    warming:   { label: "Warming up…", detail: "Initialising context, retrieving candidate history." },
    listening: {
      label: mode.id === "voice"   ? "Interview in progress…"
           : mode.id === "video"    ? "Candidate recording responses…"
           : "Interviewer live · AI transcribing…",
      detail: "Live signal streaming into the analyzer.",
    },
    scoring:   { label: "Scoring…",    detail: "Composing per-dimension scores + recommendation." },
    done:      { label: "Done",        detail: "Report ready." },
  };
  const p = phases[phase] || phases.warming;
  const Icon = mode.icon;
  return (
    <div className="p-8 text-center">
      <Icon
        className="w-8 h-8 mx-auto text-indigo-300 mb-3 animate-pulse"
        strokeWidth={1.25}
      />
      <div className="font-mono2 text-[10px] tracking-widest text-indigo-300 mb-1">
        {phase?.toUpperCase()}
      </div>
      <div className="font-display font-bold text-lg text-slate-100">
        {p.label}
      </div>
      <div className="text-[12px] text-slate-500 mt-1">{p.detail}</div>
    </div>
  );
}

/* --------- Screening report (real backend rubric) --------- */
function ScreeningReport({ data }) {
  const bandClass =
    data.band === "STRONG"
      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
      : data.band === "GOOD"
        ? "text-cyan-400 border-cyan-500/30 bg-cyan-500/10"
        : data.band === "MIXED"
          ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
          : "text-rose-400 border-rose-500/30 bg-rose-500/10";
  return (
    <div data-testid="interview-report-screening" className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-display font-bold text-lg text-slate-100">
            {data.candidate_name}
          </div>
          <div className="font-mono2 text-[10px] text-slate-500">
            recommendation · {data.recommendation.replace(/_/g, " ")}
          </div>
        </div>
        <div className="text-right">
          <div className="font-display font-black text-4xl leading-none text-emerald-300">
            {Math.round(data.composite_score * 100)}
          </div>
          <div
            className={`mt-1 inline-block px-2 py-0.5 rounded-sm border font-mono2 text-[10px] ${bandClass}`}
          >
            {data.band} · confidence {Math.round(data.confidence * 100)}%
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {data.rubric.map((d) => (
          <div
            key={d.dimension}
            className="border border-slate-800 rounded-sm p-2 bg-slate-950"
          >
            <div className="flex items-center gap-3">
              <div className="w-32 text-[12px] text-slate-100">
                {d.dimension}
              </div>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
                <div
                  className="h-full bg-emerald-400"
                  style={{ width: `${d.score * 100}%` }}
                />
              </div>
              <div className="w-14 text-right font-mono2 text-[11px] text-slate-200">
                {Math.round(d.score * 100)}
              </div>
              <div className="w-14 text-right font-mono2 text-[10px] text-slate-500">
                wt {Math.round(d.weight * 100)}%
              </div>
            </div>
            <div className="mt-1 text-[11px] text-slate-400">{d.notes}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[13px] text-slate-300 border-t border-slate-800/60 pt-3">
        {data.summary}
      </div>
    </div>
  );
}

/* --------- Voice report --------- */
function buildVoiceReport(cand, inputs) {
  return {
    candidate_name: cand?.full_name || "Candidate",
    duration_min: 11.4,
    transcript_words: 1842,
    signals: {
      technical_depth:      { score: 0.82, note: "Deep on Apex + LWC; hesitant on integration-scale." },
      structured_thinking:  { score: 0.79, note: "STAR responses ~72% of the time." },
      motivation:           { score: 0.88, note: "Volunteered 3 owned outcomes at TCS unprompted." },
      culture_signal:       { score: 0.74, note: "Prefers autonomy · aligns with LevelShift IC5 model." },
      red_flags:            { score: 0.12, note: "One inconsistent tenure claim — flagged for verify." },
    },
    focus_asked: inputs.focus_areas,
    recommendation: "advance_to_technical",
    followups: [
      "Ask about the integration-scale hesitation in the technical round.",
      "Verify tenure at TCS (2018-2021) against LinkedIn timeline.",
    ],
  };
}
function VoiceReport({ data }) {
  return (
    <div data-testid="interview-report-voice" className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-display font-bold text-lg text-slate-100">
            {data.candidate_name}
          </div>
          <div className="font-mono2 text-[10px] text-slate-500">
            {data.duration_min}m call · {data.transcript_words} words transcribed
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono2 text-[10px] tracking-widest text-emerald-400">
            RECOMMENDATION
          </div>
          <div className="font-display font-bold text-emerald-300">
            {data.recommendation.replace(/_/g, " ")}
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {Object.entries(data.signals).map(([k, s]) => (
          <SignalRow key={k} label={k} data={s} negative={k === "red_flags"} />
        ))}
      </div>
      <div className="mt-3 border-t border-slate-800/60 pt-3">
        <div className="font-mono2 text-[10px] text-slate-500 mb-1 tracking-widest">
          RECOMMENDED FOLLOWUPS
        </div>
        <ul className="text-[12.5px] text-slate-300 space-y-1">
          {data.followups.map((f, i) => (
            <li key={i}>· {f}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* --------- Copilot report --------- */
function buildCopilotReport(cand, inputs) {
  return {
    candidate_name: cand?.full_name || "Candidate",
    interviewer: inputs.interviewer || "Priya Menon",
    live_score_by_area: {
      "Coding":     { score: 0.86, note: "Solved LRU cache in 22 min, discussed tradeoffs." },
      "System Design": { score: 0.74, note: "Weak on capacity math for Kafka partitions." },
      "Behavior":   { score: 0.81, note: "Concrete conflict-resolution example (KAM)." },
    },
    ai_suggested_followups: [
      "Ask about at-scale Kafka rebalance behavior.",
      "Probe on why the last team of 4 lost 1 member.",
    ],
    ai_flags: [
      "Interviewer talking 62% of the time — try 40%.",
      "20 min left, 2 topics uncovered.",
    ],
    scorecard_draft: "Solid IC4 hire. Push to onsite. Watch for capacity-math gap.",
    recommendation: "advance_to_onsite",
  };
}
function CopilotReport({ data }) {
  return (
    <div data-testid="interview-report-copilot" className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-display font-bold text-lg text-slate-100">
            {data.candidate_name}
          </div>
          <div className="font-mono2 text-[10px] text-slate-500">
            interviewer · {data.interviewer}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono2 text-[10px] tracking-widest text-cyan-400">
            LIVE COPILOT
          </div>
          <div className="font-display font-bold text-cyan-300">
            {data.recommendation.replace(/_/g, " ")}
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {Object.entries(data.live_score_by_area).map(([k, s]) => (
          <SignalRow key={k} label={k} data={s} />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        <div className="border border-cyan-500/30 bg-cyan-500/[0.03] rounded-sm p-2">
          <div className="font-mono2 text-[10px] text-cyan-300 tracking-widest mb-1">
            AI FOLLOWUPS
          </div>
          <ul className="text-[12px] text-slate-300 space-y-1">
            {data.ai_suggested_followups.map((f, i) => (
              <li key={i}>· {f}</li>
            ))}
          </ul>
        </div>
        <div className="border border-amber-500/30 bg-amber-500/[0.03] rounded-sm p-2">
          <div className="font-mono2 text-[10px] text-amber-300 tracking-widest mb-1">
            AI FLAGS
          </div>
          <ul className="text-[12px] text-slate-300 space-y-1">
            {data.ai_flags.map((f, i) => (
              <li key={i}>· {f}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mt-3 border-t border-slate-800/60 pt-3 text-[13px] text-slate-100">
        <span className="font-mono2 text-[10px] text-slate-500 tracking-widest mr-2">
          SCORECARD DRAFT
        </span>
        {data.scorecard_draft}
      </div>
    </div>
  );
}

/* --------- Video (autonomous) report --------- */
function buildVideoReport(cand, inputs) {
  return {
    candidate_name: cand?.full_name || "Candidate",
    question_bank: inputs.question_bank || "engineering_l4_pack",
    questions: [
      { q: "Tell us about a system you built end-to-end.",
        score: 0.83, note: "Clear architecture; specific KPIs cited." },
      { q: "A tradeoff you regret.",
        score: 0.71, note: "Genuine self-reflection; light on remedy." },
      { q: "How would you scale this to 10x load?",
        score: 0.78, note: "Referenced caching + read replicas; missed backpressure." },
      { q: "Time you disagreed with a peer.",
        score: 0.85, note: "Structured & respectful." },
      { q: "Why LevelShift?",
        score: 0.88, note: "Referenced our public engineering blog." },
    ],
    integrity: {
      face_match: 0.97,
      screen_capture: "no secondary display detected",
      response_latency_pattern: "natural — no cue-card behaviour",
    },
    delivery: {
      confidence: 0.79,
      speech_rate_wpm: 148,
      filler_words_per_min: 4.2,
    },
    recommendation: "advance_to_onsite",
  };
}
function VideoReport({ data }) {
  const composite =
    data.questions.reduce((s, q) => s + q.score, 0) / (data.questions.length || 1);
  return (
    <div data-testid="interview-report-video" className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-display font-bold text-lg text-slate-100">
            {data.candidate_name}
          </div>
          <div className="font-mono2 text-[10px] text-slate-500">
            async video · {data.question_bank}
          </div>
        </div>
        <div className="text-right">
          <div className="font-display font-black text-3xl leading-none text-emerald-300">
            {Math.round(composite * 100)}
          </div>
          <div className="font-mono2 text-[10px] text-emerald-400 mt-1">
            composite
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {data.questions.map((qq, i) => (
          <div
            key={i}
            className="border border-slate-800 rounded-sm p-2 bg-slate-950"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 text-[12.5px] text-slate-100">
                Q{i + 1} · {qq.q}
              </div>
              <div className="font-mono2 text-[11px] text-slate-200">
                {Math.round(qq.score * 100)}
              </div>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">{qq.note}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        <div className="border border-emerald-500/30 bg-emerald-500/[0.03] rounded-sm p-2">
          <div className="font-mono2 text-[10px] text-emerald-300 tracking-widest mb-1 flex items-center gap-1">
            <Radio className="w-3 h-3" strokeWidth={1.5} />
            INTEGRITY
          </div>
          <div className="text-[12px] text-slate-300 space-y-1">
            <div>face-match · {Math.round(data.integrity.face_match * 100)}%</div>
            <div>screen · {data.integrity.screen_capture}</div>
            <div>latency · {data.integrity.response_latency_pattern}</div>
          </div>
        </div>
        <div className="border border-indigo-500/30 bg-indigo-500/[0.03] rounded-sm p-2">
          <div className="font-mono2 text-[10px] text-indigo-300 tracking-widest mb-1 flex items-center gap-1">
            <Bot className="w-3 h-3" strokeWidth={1.5} />
            DELIVERY
          </div>
          <div className="text-[12px] text-slate-300 space-y-1">
            <div>confidence · {Math.round(data.delivery.confidence * 100)}%</div>
            <div>speech · {data.delivery.speech_rate_wpm} wpm</div>
            <div>filler · {data.delivery.filler_words_per_min}/min</div>
          </div>
        </div>
      </div>
      <div className="mt-3 border-t border-slate-800/60 pt-3 flex items-center gap-2">
        <CheckCircle2
          className="w-4 h-4 text-emerald-400"
          strokeWidth={1.5}
        />
        <span className="text-[13px] text-slate-100">
          Recommendation · {data.recommendation.replace(/_/g, " ")}
        </span>
      </div>
    </div>
  );
}

/* --------- shared row --------- */
function SignalRow({ label, data, negative }) {
  const good = !negative;
  return (
    <div className="border border-slate-800 rounded-sm p-2 bg-slate-950">
      <div className="flex items-center gap-3">
        <div className="w-40 text-[12px] text-slate-100 capitalize">
          {label.replace(/_/g, " ")}
        </div>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
          <div
            className={`h-full ${good ? "bg-emerald-400" : "bg-rose-400"}`}
            style={{ width: `${data.score * 100}%` }}
          />
        </div>
        <div className="w-14 text-right font-mono2 text-[11px] text-slate-200">
          {Math.round(data.score * 100)}
        </div>
      </div>
      <div className="mt-1 text-[11px] text-slate-400">{data.note}</div>
    </div>
  );
}
