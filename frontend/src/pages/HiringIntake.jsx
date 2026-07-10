import React, { useState } from "react";
import {
  AlertCircle,
  Building,
  CheckCircle2,
  Clock,
  DollarSign,
  MapPin,
  MessageSquare,
  Radar,
  ShieldAlert,
  Sparkles,
  Target,
  Users2,
  Wand2,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

const EXAMPLES = [
  "We need three Senior Java Developers in Chennai. 8+ years. Spring Boot, Kafka, Microservices. Banking domain preferred. Immediate joiners.",
  "Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. Anchor architect for the Americas book. M4 level.",
  "Need a Dynamics 365 F&O consultant in Hyderabad. 5+ years, Power Platform helpful. Q2 delivery.",
  "Principal AI Product Manager in San Francisco. Owns EAROS Intelligence roadmap. LLM Ops + RAG.",
  "Client Partner for Financial Services in Boston. Own top-3 FS relationship. M4/M5.",
];

const FMT = (n, currency) => {
  if (!n) return "—";
  if (currency === "INR") return `₹${(n / 100000).toFixed(1)}L`;
  return `$${n.toLocaleString()}`;
};

function KV({ label, value, tone = "slate" }) {
  const tones = {
    slate: "text-slate-200",
    indigo: "text-indigo-300",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    rose: "text-rose-300",
  };
  return (
    <div className="p-3 border border-slate-800 bg-slate-950 rounded-sm">
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
        {label}
      </div>
      <div className={`text-[14px] ${tones[tone]}`}>{value}</div>
    </div>
  );
}

export default function HiringIntake() {
  const [brief, setBrief] = useState(EXAMPLES[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post("/intake/analyze", { brief });
      setResult(data);
    } catch (e) {
      setError(String(e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const intake = result?.intake;
  return (
    <AppLayout>
      <div data-testid={EAROS.intakeRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <MessageSquare className="w-3.5 h-3.5" strokeWidth={1.5} />
            HIRING INTAKE · CONVERSATIONAL
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Describe the hire. EAROS handles the rest.
          </h1>
          <div className="text-slate-500 text-sm max-w-3xl">
            Claude Sonnet 4.5 extracts requirements, spots ambiguities,
            recommends interview panel + sourcing channels, estimates
            compensation + time-to-fill, and generates a JD — grounded in
            LevelShift world state.
          </div>
        </div>

        {/* Input */}
        <div className="border border-slate-800 bg-slate-900 rounded-md p-4 space-y-3">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
            HIRING MANAGER BRIEF
          </div>
          <textarea
            data-testid={EAROS.intakeBriefInput}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[13px] text-slate-100 focus:outline-none focus:border-indigo-500"
          />
          <div data-testid={EAROS.intakeExamples} className="flex flex-wrap gap-1">
            <span className="font-mono2 text-[10px] text-slate-500 mr-1 self-center">
              EXAMPLES:
            </span>
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                onClick={() => setBrief(ex)}
                className="px-2 py-1 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 text-[11px]"
              >
                {ex.split(".")[0].slice(0, 42)}…
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid={EAROS.intakeRunBtn}
              onClick={analyze}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-50"
            >
              <Wand2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              {loading ? "AGENT REASONING…" : "ANALYZE BRIEF"}
            </button>
            {loading && (
              <span className="font-mono2 text-[11px] text-slate-500 flex items-center gap-1">
                <span className="pulse-dot" /> agent.intake · claude-sonnet-4.5
              </span>
            )}
            {error && <div className="text-rose-400 text-[12px]">{error}</div>}
          </div>
        </div>

        {/* Result */}
        {intake && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              <KV label="ROLE"
                  value={`${intake.role_title} · ${intake.level || "—"}`} tone="indigo" />
              <KV label="LOCATION"
                  value={<span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" strokeWidth={1.5} />
                    {intake.location || "—"}
                  </span>} />
              <KV label="HEADCOUNT" value={`× ${intake.headcount || 1}`} tone="emerald" />
              <KV label="URGENCY" value={intake.urgency || "—"} tone="amber" />
              <KV label="COMP LOW→HIGH"
                  value={`${FMT(intake.compensation_estimate_low, intake.compensation_currency)} – ${FMT(intake.compensation_estimate_high, intake.compensation_currency)}`}
                  tone="emerald" />
              <KV label="TIME-TO-FILL"
                  value={<span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" strokeWidth={1.5} />
                    {intake.expected_time_to_fill_days || "—"}d
                  </span>} />
              <KV label="DIFFICULTY"
                  value={`${Math.round((intake.difficulty_score || 0) * 100)}/100`}
                  tone={intake.difficulty_score > 0.7 ? "rose" : intake.difficulty_score > 0.5 ? "amber" : "emerald"} />
              <KV label="CONFIDENCE"
                  value={`${Math.round((intake.confidence || 0) * 100)}%`}
                  tone={intake.confidence > 0.75 ? "emerald" : "amber"} />
            </div>

            {/* Recommendation card */}
            {result?.recommendation && <AIDecisionCard rec={result.recommendation} />}

            {/* Skills */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-2">
                  MUST-HAVE SKILLS
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {intake.must_have_skills?.map((s, i) => (
                    <span key={i} className="px-2 py-1 rounded-sm border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-[12px] font-mono2">
                      {s}
                    </span>
                  ))}
                </div>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mt-4 mb-2">
                  NICE-TO-HAVE
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {intake.nice_to_have_skills?.map((s, i) => (
                    <span key={i} className="px-2 py-1 rounded-sm border border-slate-800 text-slate-400 text-[12px] font-mono2">
                      {s}
                    </span>
                  ))}
                </div>
                {intake.domain_experience?.length > 0 && (
                  <>
                    <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mt-4 mb-2">
                      DOMAIN EXPERIENCE
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {intake.domain_experience.map((s, i) => (
                        <span key={i} className="px-2 py-1 rounded-sm border border-violet-500/30 bg-violet-500/10 text-violet-300 text-[12px] font-mono2">
                          {s}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </div>

              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-amber-400 mb-2 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" strokeWidth={1.5} /> AMBIGUITIES + CLARIFYING QUESTIONS
                </div>
                <ul className="space-y-1 text-[13px] text-slate-300 mb-3">
                  {intake.ambiguities?.map((a, i) => <li key={i}>· {a}</li>)}
                  {!intake.ambiguities?.length && (
                    <li className="text-slate-500">No open questions.</li>
                  )}
                </ul>
                <ol className="space-y-1 text-[13px] text-amber-200 list-decimal list-inside">
                  {intake.clarifying_questions?.map((q, i) => <li key={i}>{q}</li>)}
                </ol>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mt-4 mb-2">
                  ASSUMPTIONS MADE
                </div>
                <ul className="space-y-1 text-[12px] text-slate-400 list-disc list-inside">
                  {intake.assumptions_made?.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            </div>

            {/* Panel + Channels */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 flex items-center gap-1">
                  <Users2 className="w-3 h-3" strokeWidth={1.5} /> RECOMMENDED INTERVIEW PANEL
                </div>
                <ul className="space-y-2">
                  {intake.recommended_interview_panel?.map((p, i) => (
                    <li key={i} className="text-[13px]">
                      <span className="text-slate-100 font-medium">{p.role}</span>
                      <span className="text-slate-500"> — {p.why}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 flex items-center gap-1">
                  <Radar className="w-3 h-3" strokeWidth={1.5} /> SOURCING CHANNEL PLAN
                </div>
                <ul className="space-y-2">
                  {intake.recommended_sourcing_channels?.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px]">
                      <span className={`shrink-0 px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                        c.priority === "P0"
                          ? "text-rose-400 border-rose-500/30 bg-rose-500/10"
                          : c.priority === "P1"
                            ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                            : "text-slate-400 border-slate-500/30 bg-slate-500/10"
                      }`}>
                        {c.priority}
                      </span>
                      <div>
                        <div className="text-slate-100">{c.channel}</div>
                        <div className="text-slate-500 text-[12px]">{c.why}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* JD + Rubric */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-2 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" strokeWidth={1.5} /> GENERATED JOB DESCRIPTION
                </div>
                <div className="font-display text-lg font-bold text-slate-100 mb-1">
                  {intake.generated_jd?.title}
                </div>
                <div className="italic text-slate-400 text-[13px] mb-3">
                  {intake.generated_jd?.one_liner}
                </div>
                <div className="mb-3">
                  <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                    RESPONSIBILITIES
                  </div>
                  <ul className="space-y-0.5 text-[13px] text-slate-300 list-disc list-inside">
                    {intake.generated_jd?.responsibilities?.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
                <div className="mb-3">
                  <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                    REQUIREMENTS
                  </div>
                  <ul className="space-y-0.5 text-[13px] text-slate-300 list-disc list-inside">
                    {intake.generated_jd?.requirements?.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
                <div className="text-[12px] text-slate-400 border-t border-slate-800/60 pt-2 mt-2">
                  <span className="text-slate-500 font-mono2">team: </span>
                  {intake.generated_jd?.team_context}
                </div>
                <div className="text-[12px] text-slate-400">
                  <span className="text-slate-500 font-mono2">growth: </span>
                  {intake.generated_jd?.growth_path}
                </div>
              </div>

              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-amber-400 mb-2 flex items-center gap-1">
                  <Target className="w-3 h-3" strokeWidth={1.5} /> SCREENING RUBRIC (8-DIM)
                </div>
                <div className="space-y-2">
                  {intake.screening_rubric?.map((d, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-28 text-[12px] text-slate-300">{d.dimension}</div>
                      <div className="flex-1 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
                        <div
                          className="h-full bg-amber-400"
                          style={{ width: `${(d.weight || 0) * 100}%` }}
                        />
                      </div>
                      <div className="w-10 text-right font-mono2 text-[11px] text-slate-400">
                        {Math.round((d.weight || 0) * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Risks */}
            {intake.hiring_risks?.length > 0 && (
              <div className="border border-rose-500/30 bg-rose-500/5 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-rose-400 mb-2 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" strokeWidth={1.5} /> HIRING RISKS
                </div>
                <ul className="space-y-1 text-[13px] text-rose-200 list-disc list-inside">
                  {intake.hiring_risks.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}

            <div className="text-[11px] font-mono2 text-slate-500 text-right">
              intake · {intake.source || "unknown"} · confidence{" "}
              {Math.round((intake.confidence || 0) * 100)}%
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
