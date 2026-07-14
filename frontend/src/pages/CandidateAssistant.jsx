import React, { useState } from "react";
import {
  Award,
  BookOpen,
  Building2,
  CheckCircle2,
  Clock,
  Coffee,
  Search,
  Sunrise,
  Sunset,
  Target,
  Users2,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const FAQ = [
  {
    q: "How do I check my application status?",
    a: "Use the lookup on the right — your candidate_id is in your welcome email.",
  },
  {
    q: "When will I hear back?",
    a: "LevelShift averages 3–5 business days between stages. Time-sensitive updates come from your recruiter.",
  },
  {
    q: "Can I reschedule an interview?",
    a: "Yes — reply to your recruiter's latest email and propose two windows.",
  },
  {
    q: "How do offers work?",
    a: "Every offer at LevelShift requires human approval. AI recommends bands; hiring leaders decide.",
  },
];

export default function CandidateAssistant() {
  const [tab, setTab] = useState("status");
  const [id, setId] = useState("cand_ai_staff_bang_00");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const lookup = async () => {
    setLoading(true);
    setErr(null);
    try {
      const { data } = await api.get(`/apps/candidate/${id}/status`);
      setStatus(data);
    } catch (e) {
      setErr("Candidate not found. Try `cand_ai_staff_bang_00`.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.candidateAssistantRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            CANDIDATE ASSISTANT
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Your prep agent for LevelShift
          </h1>
          <div className="text-slate-500 text-sm">
            Track your progress, prep for interviews, understand the org, and
            preview a day in the life. Nothing confidential ever crosses this
            boundary.
          </div>
        </div>

        {/* Tab selector */}
        <div
          data-testid="candidate-tabs"
          className="border-b border-slate-800 flex items-center gap-1"
        >
          {[
            { id: "status",    label: "Status",           icon: Target },
            { id: "prep",      label: "Interview prep",   icon: BookOpen },
            { id: "org",       label: "Org overview",     icon: Building2 },
            { id: "day",       label: "Day in the life",  icon: Coffee },
          ].map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                data-testid={`candidate-tab-${t.id}`}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 -mb-px font-mono2 text-[11px] tracking-widest transition ${
                  active
                    ? "border-indigo-400 text-indigo-300"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                {t.label.toUpperCase()}
              </button>
            );
          })}
        </div>

        {tab === "status" && (
          <StatusView
            id={id}
            setId={setId}
            status={status}
            loading={loading}
            err={err}
            lookup={lookup}
          />
        )}
        {tab === "prep" && <InterviewPrep />}
        {tab === "org" && <OrgOverview />}
        {tab === "day" && <DayInLife />}
      </div>
    </AppLayout>
  );
}

function StatusView({ id, setId, status, loading, err, lookup }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-3">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
          STATUS LOOKUP
        </div>
        <div className="flex gap-2">
          <input
            data-testid={EAROS.candidateIdInput}
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="candidate_id"
            className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[13px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500"
          />
          <button
            data-testid={EAROS.candidateLookupBtn}
            onClick={lookup}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2 disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" strokeWidth={1.5} />
            {loading ? "…" : "LOOKUP"}
          </button>
        </div>
        {err && <div className="text-rose-400 text-[12px]">{err}</div>}
        {status && (
          <div className="border border-slate-800 bg-slate-950 rounded-sm p-4 space-y-2">
            <div className="font-display text-lg font-bold text-slate-100">
              {status.full_name}
            </div>
            <div className="text-slate-400 text-[13px]">
              {status.job_title} · {status.location}
            </div>
            <div className="flex items-center gap-2 mt-3">
              <span className="font-mono2 text-[10px] tracking-widest text-slate-500">
                STAGE
              </span>
              <span className="px-1.5 py-0.5 rounded-sm border font-mono2 text-[11px] text-emerald-400 bg-emerald-500/10 border-emerald-500/30">
                {status.stage}
              </span>
            </div>
            <div className="mt-3">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                NEXT STEP
              </div>
              <div className="text-slate-200 text-[13px]">
                {status.next_step}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-3">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
          FAQ
        </div>
        <div className="space-y-3">
          {FAQ.map((f, i) => (
            <div
              key={i}
              className="border-b border-slate-800/60 pb-3 last:border-b-0"
            >
              <div className="text-slate-100 text-[13px] font-medium">
                {f.q}
              </div>
              <div className="text-slate-400 text-[12px] mt-1">{f.a}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   TASK 10 — Candidate-prep agent tabs
   ============================================================ */

const STAGES_WALKTHROUGH = [
  {
    key: "screening",
    label: "AI Screening",
    duration: "5 min · async",
    what: "A short structured screen — technical + culture. AI scores 8 dimensions.",
    tips: [
      "Answer concretely — 'I' more than 'we'.",
      "STAR framework: Situation → Task → Action → Result.",
      "Numbers > adjectives. 'Reduced latency 40%' beats 'made it fast'.",
    ],
  },
  {
    key: "phone_screen",
    label: "Recruiter phone screen",
    duration: "20 min · live",
    what: "Get-to-know call with a recruiter — motivations, comp, location, timing.",
    tips: [
      "Have your comp expectations ready with a rationale.",
      "Ask about the team's mission and the hiring manager's style.",
      "Confirm process timeline so you can plan.",
    ],
  },
  {
    key: "technical",
    label: "Technical interview",
    duration: "60 min · live",
    what: "Coding + system design + a scoping question. AI Copilot assists the interviewer live.",
    tips: [
      "Think out loud. Silence hurts more than a wrong direction.",
      "Clarify constraints for 90 seconds before touching code.",
      "Discuss tradeoffs even after you've picked an approach.",
    ],
  },
  {
    key: "onsite",
    label: "Onsite (or virtual onsite)",
    duration: "3 rounds · half day",
    what: "Panel of 3: technical deep-dive, cross-functional, and skip-level.",
    tips: [
      "Have 3 questions per round. Different questions per interviewer.",
      "The skip-level round is about ambition + judgment, not trivia.",
      "Bring specific examples from your current role.",
    ],
  },
  {
    key: "offer",
    label: "Offer",
    duration: "24-72h",
    what: "Every offer requires human approval. AI proposes bands; leaders sign.",
    tips: [
      "Ask for total-comp breakdown (base, equity, sign-on, bonus).",
      "You may negotiate — data-backed asks land better than vague ones.",
      "Take 48h to decide. Never rushed.",
    ],
  },
];

function InterviewPrep() {
  const [open, setOpen] = useState(STAGES_WALKTHROUGH[0].key);
  return (
    <div
      data-testid="candidate-prep"
      className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-3"
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2">
        <BookOpen className="w-3 h-3" strokeWidth={1.5} />
        INTERVIEW WALKTHROUGH — 5 STAGES
      </div>
      <div className="space-y-2">
        {STAGES_WALKTHROUGH.map((s, i) => {
          const active = open === s.key;
          return (
            <div
              key={s.key}
              data-testid={`candidate-stage-${s.key}`}
              className={`border rounded-sm ${
                active
                  ? "border-indigo-500/40 bg-indigo-500/[0.03]"
                  : "border-slate-800 bg-slate-950/50"
              }`}
            >
              <button
                onClick={() => setOpen(active ? null : s.key)}
                className="w-full text-left px-4 py-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="font-mono2 text-[10px] text-indigo-400 shrink-0">
                    STAGE 0{i + 1}
                  </div>
                  <div className="text-slate-100 text-[13px] font-medium truncate">
                    {s.label}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 text-slate-500 font-mono2 text-[10px]">
                  <Clock className="w-3 h-3" strokeWidth={1.5} />
                  {s.duration}
                </div>
              </button>
              {active && (
                <div className="px-4 pb-4 space-y-2">
                  <div className="text-[13px] text-slate-300">{s.what}</div>
                  <ul className="space-y-1 text-[12.5px] text-slate-200">
                    {s.tips.map((t, j) => (
                      <li key={j} className="flex gap-2">
                        <CheckCircle2
                          className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"
                          strokeWidth={1.5}
                        />
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OrgOverview() {
  return (
    <div
      data-testid="candidate-org"
      className="grid grid-cols-1 lg:grid-cols-2 gap-4"
    >
      <div className="border border-slate-800 bg-slate-900 rounded-md p-5">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2 mb-2">
          <Building2 className="w-3 h-3" strokeWidth={1.5} />
          WHO WE ARE
        </div>
        <div className="font-display font-black text-2xl text-slate-100 mb-2">
          LevelShift
        </div>
        <div className="text-slate-300 text-[13px] leading-relaxed">
          A 237-person enterprise AI + digital services firm. We build for
          Fortune 500 buyers in banking, retail, and healthcare — deeply
          embedded on Salesforce, Dynamics 365, and modern data + AI platforms.
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-[12px]">
          <MetaLine label="Founded" value="2018" />
          <MetaLine label="HQ" value="Bangalore · New York" />
          <MetaLine label="Employees" value="237" />
          <MetaLine label="Open reqs" value="12 · 5 P0" />
        </div>
      </div>

      <div className="border border-slate-800 bg-slate-900 rounded-md p-5">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2 mb-2">
          <Award className="w-3 h-3" strokeWidth={1.5} />
          WHAT WE VALUE
        </div>
        <ul className="space-y-2 text-[13px] text-slate-100">
          <li className="flex gap-2">
            <Target className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" strokeWidth={1.5} />
            <span>
              <strong>Outcomes, not activity.</strong> We measure by client
              impact, not standups shipped.
            </span>
          </li>
          <li className="flex gap-2">
            <Users2 className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" strokeWidth={1.5} />
            <span>
              <strong>Craft in public.</strong> Every practice area writes,
              open-sources, and speaks.
            </span>
          </li>
          <li className="flex gap-2">
            <BookOpen className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" strokeWidth={1.5} />
            <span>
              <strong>Curiosity is a promotion criteria.</strong> We fund one
              deep-dive project per quarter for every senior engineer.
            </span>
          </li>
          <li className="flex gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" strokeWidth={1.5} />
            <span>
              <strong>Ethical AI is table stakes.</strong> Every AI decision at
              LevelShift is explainable and gated.
            </span>
          </li>
        </ul>
      </div>

      <div className="lg:col-span-2 border border-slate-800 bg-slate-900 rounded-md p-5">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2 mb-3">
          <Users2 className="w-3 h-3" strokeWidth={1.5} />
          DEPARTMENTS — WHERE YOU MIGHT LAND
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 text-[12px]">
          {[
            { name: "Salesforce Practice", size: 68, focus: "Apex · LWC · CPQ" },
            { name: "Dynamics 365 Practice", size: 42, focus: "F&O · CE" },
            { name: "AI Engineering", size: 34, focus: "LLM Ops · Agents" },
            { name: "Data Engineering", size: 51, focus: "Lakehouse · Streaming" },
            { name: "Enterprise Sales", size: 22, focus: "Field · Alliances" },
          ].map((d) => (
            <div
              key={d.name}
              className="p-3 border border-slate-800 bg-slate-950/50 rounded-sm"
            >
              <div className="text-slate-100 text-[13px] font-medium">
                {d.name}
              </div>
              <div className="font-mono2 text-[10px] text-slate-500 mt-1">
                {d.size} people
              </div>
              <div className="text-slate-400 text-[11px] mt-1">{d.focus}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DayInLife() {
  const day = [
    { icon: Sunrise, time: "08:30", label: "Async standup",
      detail: "Post a written update; read 4 peers'. No meetings." },
    { icon: Coffee, time: "09:30", label: "Deep-work block",
      detail: "3 uninterrupted hours. No Slack. Kernel of the day." },
    { icon: Users2, time: "12:30", label: "Client sync",
      detail: "45 min — one high-signal working session with your client counterpart." },
    { icon: BookOpen, time: "14:00", label: "Learning hour",
      detail: "One paper, one prototype, one demo per week — funded by the practice." },
    { icon: Target, time: "15:30", label: "Second deep-work block",
      detail: "Ship the thing you promised in standup." },
    { icon: Users2, time: "17:00", label: "Peer review",
      detail: "30 min pairing / code review with a senior engineer." },
    { icon: Sunset, time: "18:30", label: "Log off",
      detail: "No 9pm 'quick asks'. If it's urgent, we page." },
  ];
  return (
    <div
      data-testid="candidate-day"
      className="border border-slate-800 bg-slate-900 rounded-md p-5"
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2 mb-3">
        <Coffee className="w-3 h-3" strokeWidth={1.5} />
        A DAY IN THE LIFE · SENIOR ENGINEER
      </div>
      <div className="space-y-2">
        {day.map((d, i) => {
          const Icon = d.icon;
          return (
            <div
              key={i}
              className="flex items-start gap-3 p-3 border border-slate-800 bg-slate-950/50 rounded-sm"
            >
              <div className="font-mono2 text-indigo-400 text-[11px] w-14 shrink-0">
                {d.time}
              </div>
              <Icon
                className="w-4 h-4 text-indigo-300 shrink-0 mt-0.5"
                strokeWidth={1.5}
              />
              <div className="min-w-0 flex-1">
                <div className="text-slate-100 text-[13px] font-medium">
                  {d.label}
                </div>
                <div className="text-slate-400 text-[12px]">{d.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetaLine({ label, value }) {
  return (
    <div>
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500 uppercase">
        {label}
      </div>
      <div className="text-slate-200 text-[13px] font-medium">{value}</div>
    </div>
  );
}
