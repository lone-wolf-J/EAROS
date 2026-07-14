import React, { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import {
  Bot,
  Clock,
  Cpu,
  DollarSign,
  GitBranch,
  History,
  Layers,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const LANE_META = {
  planner: { label: "PLANNER", color: "indigo", icon: GitBranch },
  policy: { label: "POLICY ENGINE", color: "rose", icon: ShieldAlert },
  runtime: { label: "EXECUTION RUNTIME", color: "cyan", icon: Cpu },
  capability: { label: "CAPABILITY REGISTRY", color: "amber", icon: Layers },
  world: { label: "WORLD STATE", color: "emerald", icon: Bot },
  governance: { label: "GOVERNANCE", color: "violet", icon: ShieldCheck },
  reflection: { label: "REFLECTION", color: "violet", icon: Sparkles },
};

const COLOR_CSS = {
  indigo: {
    dot: "bg-indigo-400", text: "text-indigo-300",
    border: "border-indigo-500/40", bg: "bg-indigo-500/10",
  },
  cyan: {
    dot: "bg-cyan-400", text: "text-cyan-300",
    border: "border-cyan-500/40", bg: "bg-cyan-500/10",
  },
  rose: {
    dot: "bg-rose-400", text: "text-rose-300",
    border: "border-rose-500/40", bg: "bg-rose-500/10",
  },
  amber: {
    dot: "bg-amber-400", text: "text-amber-300",
    border: "border-amber-500/40", bg: "bg-amber-500/10",
  },
  emerald: {
    dot: "bg-emerald-400", text: "text-emerald-300",
    border: "border-emerald-500/40", bg: "bg-emerald-500/10",
  },
  violet: {
    dot: "bg-violet-400", text: "text-violet-300",
    border: "border-violet-500/40", bg: "bg-violet-500/10",
  },
};

function laneIndex(lanes, key) {
  return lanes.indexOf(key);
}

export default function DeepDive() {
  const { data: executions } = useSWR("/deep-dive/executions", fetcher, {
    refreshInterval: 5000,
  });
  const [correlationId, setCorrelationId] = useState(null);
  const [replay, setReplay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(400); // ms between reveals
  const [visibleCount, setVisibleCount] = useState(0);
  const [selectedMsg, setSelectedMsg] = useState(null);

  useEffect(() => {
    if (executions?.length && !correlationId) {
      setCorrelationId(executions[0].correlation_id);
    }
  }, [executions, correlationId]);

  const load = async (cid) => {
    setLoading(true);
    setReplay(null);
    setVisibleCount(0);
    setPlaying(false);
    setSelectedMsg(null);
    try {
      const { data } = await api.get(`/deep-dive/replay/${cid}`);
      setReplay(data);
      setVisibleCount(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (correlationId) load(correlationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [correlationId]);

  // Animation
  useEffect(() => {
    if (!playing || !replay) return;
    if (visibleCount >= replay.messages.length) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setVisibleCount((v) => v + 1), speed);
    return () => clearTimeout(t);
  }, [playing, visibleCount, replay, speed]);

  const currentMessages = useMemo(() => {
    if (!replay) return [];
    return replay.messages.slice(0, visibleCount);
  }, [replay, visibleCount]);

  const lanes = replay?.lanes || Object.keys(LANE_META);
  const [view, setView] = useState("swimlane"); // "swimlane" | "architecture"

  return (
    <AppLayout>
      <div data-testid={EAROS.deepDiveRoot} className="p-6 space-y-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
              <History className="w-3.5 h-3.5" strokeWidth={1.5} />
              DEEP-DIVE · AGENT-TO-AGENT REPLAY
            </div>
            <h1 className="font-display text-3xl font-black tracking-tight">
              Watch every layer participate.
            </h1>
            <div className="text-slate-500 text-sm max-w-3xl">
              Replay any past execution — Planner, Policy Engine, Runtime,
              Capability Registry, World State, Governance, and Reflection —
              with real payloads, confidence, and human approval pauses.
            </div>
          </div>
          <div
            data-testid="deepdive-view-toggle"
            className="inline-flex items-center gap-0 border border-slate-800 rounded-sm bg-slate-950/60 p-0.5 shrink-0"
          >
            {[
              { id: "swimlane",     label: "SWIMLANE" },
              { id: "architecture", label: "ARCHITECTURE" },
            ].map((v) => (
              <button
                key={v.id}
                data-testid={`deepdive-view-${v.id}`}
                onClick={() => setView(v.id)}
                className={`px-2.5 py-1.5 rounded-sm font-mono2 text-[10px] tracking-widest transition ${
                  view === v.id
                    ? "bg-indigo-500/25 text-indigo-200 border border-indigo-500/40"
                    : "text-slate-500 hover:text-slate-300 border border-transparent"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
        {view === "architecture" && <LayeredArchitecture />}

        {view === "swimlane" && (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
          {/* Execution picker */}
          <div className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden">
            <div className="p-3 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
              REPLAYABLE EXECUTIONS
            </div>
            <div className="max-h-[560px] overflow-y-auto divide-y divide-slate-800/60">
              {(executions || []).map((e) => (
                <button
                  key={e.correlation_id}
                  data-testid={EAROS.deepDiveExecutionRow(e.correlation_id)}
                  onClick={() => setCorrelationId(e.correlation_id)}
                  className={`w-full text-left px-3 py-2.5 text-[12px] transition-colors ${
                    correlationId === e.correlation_id
                      ? "bg-slate-800/60 border-l-2 border-l-indigo-500"
                      : "hover:bg-slate-900/60 border-l-2 border-l-transparent"
                  }`}
                >
                  <div className="text-slate-100 line-clamp-2">{e.goal}</div>
                  <div className="mt-1 flex items-center justify-between font-mono2 text-[10px] text-slate-500">
                    <span>{e.kind}</span>
                    <span className={
                      e.status === "succeeded" ? "text-emerald-400" :
                      e.status === "failed" ? "text-rose-400" :
                      e.status === "policy_blocked" ? "text-rose-400" :
                      e.status === "awaiting_approval" ? "text-amber-400" :
                      "text-slate-400"
                    }>{e.status}</span>
                  </div>
                  <div className="font-mono2 text-[9px] text-slate-600 mt-0.5">
                    {e.started_at?.slice(11, 19)} · {e.steps} step(s)
                  </div>
                </button>
              ))}
              {!executions?.length && (
                <div className="p-4 text-slate-500 text-[11px]">
                  No executions yet — run a scenario or approve a recommendation.
                </div>
              )}
            </div>
          </div>

          {/* Replay canvas */}
          <div className="space-y-3">
            {/* Controls + roll-up */}
            <div className="border border-slate-800 bg-slate-900 rounded-md p-3 flex flex-wrap items-center gap-3">
              <button
                data-testid={EAROS.deepDivePlayBtn}
                onClick={() => {
                  if (visibleCount >= (replay?.messages?.length || 0)) {
                    setVisibleCount(0);
                  }
                  setPlaying((p) => !p);
                }}
                disabled={!replay || replay.messages.length === 0}
                className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
              >
                {playing ? <Pause className="w-3.5 h-3.5" strokeWidth={2} /> : <Play className="w-3.5 h-3.5" strokeWidth={2} />}
                {playing ? "PAUSE" : visibleCount === 0 ? "PLAY" : "RESUME"}
              </button>
              <button
                onClick={() => { setVisibleCount(0); setPlaying(false); }}
                disabled={!replay}
                className="flex items-center gap-1 px-2 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2 disabled:opacity-40"
              >
                <RotateCcw className="w-3.5 h-3.5" strokeWidth={1.5} />
                RESET
              </button>
              <button
                onClick={() => setVisibleCount(replay?.messages?.length || 0)}
                disabled={!replay}
                className="px-2 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2 disabled:opacity-40"
              >
                SHOW ALL
              </button>
              <div className="flex items-center gap-2 ml-2">
                <span className="font-mono2 text-[10px] text-slate-500">SPEED</span>
                {[800, 400, 150].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSpeed(s)}
                    className={`px-2 py-1 rounded-sm border font-mono2 text-[10px] ${
                      speed === s
                        ? "border-indigo-500 text-indigo-300 bg-indigo-500/10"
                        : "border-slate-800 text-slate-400"
                    }`}
                  >
                    {s === 800 ? "0.5×" : s === 400 ? "1×" : "3×"}
                  </button>
                ))}
              </div>

              <div className="ml-auto flex items-center gap-4 text-[11px] font-mono2">
                <div className="flex items-center gap-1 text-slate-400">
                  <Clock className="w-3 h-3" strokeWidth={1.5} />
                  {replay ? `${replay.duration_ms}ms` : "—"}
                </div>
                <div className="flex items-center gap-1 text-slate-400">
                  <DollarSign className="w-3 h-3" strokeWidth={1.5} />
                  {replay ? `$${replay.total_cost_usd.toFixed(4)}` : "—"}
                </div>
                <div className="flex items-center gap-1 text-emerald-400">
                  auto-approved · {replay?.auto_approved ?? 0}
                </div>
                <div className="flex items-center gap-1 text-amber-400">
                  human-gated · {replay?.human_gated ?? 0}
                </div>
              </div>
            </div>

            {/* Swimlane */}
            <div className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden">
              {loading && (
                <div className="p-8 text-center text-slate-500 font-mono2 text-[11px]">
                  loading replay…
                </div>
              )}
              {!loading && replay && (
                <div className="p-4 overflow-x-auto">
                  <div className="min-w-[900px]">
                    {/* Lane headers */}
                    <div className="grid grid-cols-7 gap-2 mb-3">
                      {lanes.map((lane) => {
                        const meta = LANE_META[lane];
                        const col = COLOR_CSS[meta.color];
                        const Icon = meta.icon;
                        return (
                          <div key={lane}
                               className={`p-2 rounded-sm border ${col.border} ${col.bg}`}>
                            <div className={`flex items-center gap-1 font-mono2 text-[10px] tracking-widest ${col.text}`}>
                              <Icon className="w-3 h-3" strokeWidth={1.5} />
                              {meta.label}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Messages grid */}
                    <div className="space-y-2">
                      {currentMessages.map((m, idx) => {
                        const col = COLOR_CSS[LANE_META[m.lane]?.color || "indigo"];
                        const laneIdx = laneIndex(lanes, m.lane);
                        return (
                          <div key={m.event_id} className="grid grid-cols-7 gap-2">
                            {lanes.map((l, i) => {
                              if (i !== laneIdx) {
                                return <div key={l} className="h-14" />;
                              }
                              const isSelected = selectedMsg?.event_id === m.event_id;
                              return (
                                <button
                                  key={l}
                                  data-testid={EAROS.deepDiveMessage(m.event_id)}
                                  onClick={() => setSelectedMsg(m)}
                                  className={`h-14 p-2 border rounded-sm text-left transition-colors relative ${
                                    isSelected
                                      ? `${col.border} ${col.bg}`
                                      : `border-slate-800 bg-slate-950 hover:${col.border}`
                                  }`}
                                >
                                  <div className={`absolute -top-1 -left-1 w-2 h-2 rounded-full ${col.dot} ${idx === visibleCount - 1 ? "animate-ping" : ""}`} />
                                  <div className={`font-mono2 text-[9px] ${col.text} tracking-widest truncate`}>
                                    {m.label}
                                  </div>
                                  <div className="text-slate-200 text-[11px] mt-0.5 line-clamp-2">
                                    {m.human || m.event_type}
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        );
                      })}
                      {currentMessages.length === 0 && (
                        <div className="text-center text-slate-500 text-[12px] py-8">
                          Press <span className="font-mono2 text-indigo-400">PLAY</span> to
                          replay the execution.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Selected message detail */}
            {selectedMsg && (
              <div className="border border-indigo-500/40 bg-indigo-500/5 rounded-md p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="font-mono2 text-[10px] tracking-widest text-indigo-400">
                      MESSAGE DETAIL · {selectedMsg.event_type}
                    </div>
                    <div className="font-display text-base font-bold text-slate-100">
                      {selectedMsg.label}
                    </div>
                  </div>
                  <div className="font-mono2 text-[10px] text-slate-500 text-right">
                    <div>{selectedMsg.occurred_at?.slice(0, 19)}</div>
                    <div>lane · {selectedMsg.lane}</div>
                  </div>
                </div>
                <div className="text-[13px] text-slate-200 mb-3">{selectedMsg.human}</div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">ACTOR</div>
                    <div className="text-slate-100">{selectedMsg.actor || "—"}</div>
                    <div className="font-mono2 text-[10px] text-slate-500 mt-2 mb-1">SUBJECT</div>
                    <div className="text-slate-100 truncate">
                      {selectedMsg.subject_type}:{selectedMsg.subject_id}
                    </div>
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">CAPABILITY</div>
                    <div className="text-slate-100 font-mono2">
                      {selectedMsg.capability_id || "—"}
                    </div>
                    {selectedMsg.confidence !== null && selectedMsg.confidence !== undefined && (
                      <>
                        <div className="font-mono2 text-[10px] text-slate-500 mt-2 mb-1">CONFIDENCE</div>
                        <div className="text-emerald-300 font-mono2">
                          {Math.round((selectedMsg.confidence || 0) * 100)}%
                        </div>
                      </>
                    )}
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">POLICIES</div>
                    {selectedMsg.policies?.length ? (
                      <div className="flex flex-wrap gap-1">
                        {selectedMsg.policies.map((p) => (
                          <span key={p.policy_id}
                                className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                                  p.decision === "allow" ?
                                    "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" :
                                  p.decision === "deny" ?
                                    "text-rose-400 border-rose-500/30 bg-rose-500/10" :
                                    "text-amber-400 border-amber-500/30 bg-amber-500/10"
                                }`}
                                title={p.reason}>
                            {p.name} · {p.decision}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="text-slate-500 text-[11px]">—</div>
                    )}
                  </div>
                </div>

                {/* Payload — human field-by-field, no raw JSON */}
                {Object.keys(selectedMsg.payload || {}).length > 0 && (
                  <div className="mt-3">
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">PAYLOAD</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-[11px] font-mono2">
                      {Object.entries(selectedMsg.payload)
                        .filter(([k]) => !["policies"].includes(k))
                        .map(([k, v]) => (
                          <div key={k} className="flex gap-2 border border-slate-800 bg-slate-950 rounded-sm px-2 py-1">
                            <span className="text-slate-500 shrink-0">{k}</span>
                            <span className="text-slate-200 truncate" title={typeof v === "object" ? JSON.stringify(v) : String(v)}>
                              {typeof v === "boolean" ? (v ? "yes" : "no") :
                               typeof v === "object" ? `${Array.isArray(v) ? v.length + " item(s)" : Object.keys(v).length + " field(s)"}` :
                               String(v).slice(0, 80)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Approvals for this run */}
            {replay?.approvals?.length > 0 && (
              <div className="border border-amber-500/30 bg-amber-500/5 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-amber-400 mb-2 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" strokeWidth={1.5} />
                  HUMAN APPROVAL PAUSE POINTS
                </div>
                <ul className="space-y-1 text-[12px]">
                  {replay.approvals.map((a) => (
                    <li key={a.approval_id} className="flex items-center gap-2">
                      <span className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${
                        a.status === "granted"
                          ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                          : a.status === "denied"
                            ? "text-rose-400 border-rose-500/30 bg-rose-500/10"
                            : "text-amber-400 border-amber-500/30 bg-amber-500/10"
                      }`}>
                        {a.status.toUpperCase()}
                      </span>
                      <span className="text-slate-200 flex-1 truncate">{a.reason}</span>
                      <span className="font-mono2 text-[10px] text-slate-500">
                        {a.decided_by || "awaiting"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        )}
      </div>
    </AppLayout>
  );
}


/* ============================================================
   TASK 11 — Layered agent architecture diagram
   ============================================================ */

const ARCH_LAYERS = [
  {
    key: "business",
    label: "Business layer",
    color: "indigo",
    tagline: "The 'why' — outcomes leaders can steer",
    nodes: [
      { id: "policy_mgr",  name: "Policy Manager",     what: "Fairness, PII, DEI, comp bands." },
      { id: "objectives",  name: "Objectives",         what: "Portfolio-level hiring targets." },
      { id: "goverance_ui",name: "Governance",         what: "Immutable audit; who signed off." },
    ],
  },
  {
    key: "decision",
    label: "Decision layer",
    color: "cyan",
    tagline: "The 'what' — where AI proposes plans",
    nodes: [
      { id: "planner",     name: "Planner",            what: "Claude 4.5 · schema-validated plans." },
      { id: "policy_eng",  name: "Policy Engine",      what: "Evaluates every step before execution." },
      { id: "strategist",  name: "Strategy Agent",     what: "Skill scarcity + workforce simulation." },
      { id: "reflect",     name: "Reflection",         what: "What worked, what to change." },
    ],
  },
  {
    key: "execution",
    label: "Execution layer",
    color: "emerald",
    tagline: "The 'how' — deterministic tools that DO",
    nodes: [
      { id: "runtime",     name: "Runtime",            what: "Executes steps, records events." },
      { id: "cap_reg",     name: "Capability Registry",what: "The catalog of callable actions." },
      { id: "sourcing",    name: "Sourcing Agent",     what: "Parallel scan across 10 channels." },
      { id: "outreach",    name: "Outreach Agent",     what: "Per-tone message packs." },
      { id: "screen",      name: "Screening Agent",    what: "8-dim rubric + async voice + video." },
    ],
  },
  {
    key: "knowledge",
    label: "Knowledge layer",
    color: "amber",
    tagline: "Grounded facts — no hallucinations",
    nodes: [
      { id: "world",       name: "World State",        what: "Candidates, reqs, offers, events." },
      { id: "memory",      name: "Episodic Memory",    what: "Prior recommendations + outcomes." },
      { id: "skill_graph", name: "Skill Graph",        what: "Structured skills, supply/demand." },
    ],
  },
  {
    key: "infra",
    label: "Infrastructure layer",
    color: "violet",
    tagline: "The plumbing — boring, dependable",
    nodes: [
      { id: "event_bus",   name: "Event Bus",          what: "Append-only, replayable." },
      { id: "auth",        name: "Auth · Google OAuth",what: "Roles: recruiter, HM, exec, admin." },
      { id: "obs",         name: "Observability",      what: "Latency, cost, health per agent." },
      { id: "storage",     name: "Storage · MongoDB",  what: "Event stream + world state." },
    ],
  },
];

const ARCH_COLORS = {
  indigo:  { border: "border-indigo-500/40",  text: "text-indigo-300",  bg: "bg-indigo-500/[0.05]" },
  cyan:    { border: "border-cyan-500/40",    text: "text-cyan-300",    bg: "bg-cyan-500/[0.05]" },
  emerald: { border: "border-emerald-500/40", text: "text-emerald-300", bg: "bg-emerald-500/[0.05]" },
  amber:   { border: "border-amber-500/40",   text: "text-amber-300",   bg: "bg-amber-500/[0.05]" },
  violet:  { border: "border-violet-500/40",  text: "text-violet-300",  bg: "bg-violet-500/[0.05]" },
};

function LayeredArchitecture() {
  const [openNode, setOpenNode] = useState(null);
  return (
    <div
      data-testid="architecture-diagram"
      className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden"
    >
      <div className="p-4 border-b border-slate-800/60">
        <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-1">
          EAROS · LAYERED AGENT ARCHITECTURE
        </div>
        <div className="text-slate-400 text-[13px]">
          Intelligence separated from execution. Five layers, each independently
          testable, replaceable, and audited. Click a node for its role.
        </div>
      </div>
      <div className="p-4 space-y-3">
        {ARCH_LAYERS.map((layer) => {
          const c = ARCH_COLORS[layer.color];
          return (
            <div
              key={layer.key}
              data-testid={`arch-layer-${layer.key}`}
              className={`border ${c.border} ${c.bg} rounded-sm`}
            >
              <div className="px-3 py-2 border-b border-slate-800/50 flex items-baseline justify-between gap-3">
                <div>
                  <div className={`font-mono2 text-[10px] tracking-widest ${c.text}`}>
                    {layer.label.toUpperCase()}
                  </div>
                  <div className="text-slate-100 text-[12px]">{layer.tagline}</div>
                </div>
                <div className="font-mono2 text-[10px] text-slate-500">
                  {layer.nodes.length} nodes
                </div>
              </div>
              <div className="p-2 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
                {layer.nodes.map((n) => {
                  const open = openNode === n.id;
                  return (
                    <button
                      key={n.id}
                      data-testid={`arch-node-${n.id}`}
                      onClick={() => setOpenNode(open ? null : n.id)}
                      className={`text-left p-2 rounded-sm border transition ${
                        open
                          ? `${c.border} bg-slate-950 ring-1 ring-indigo-500/30`
                          : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                      }`}
                    >
                      <div className="text-slate-100 text-[12px] font-medium truncate">
                        {n.name}
                      </div>
                      <div className="font-mono2 text-[10px] text-slate-500 truncate mt-0.5">
                        {n.id}
                      </div>
                      {open && (
                        <div className="text-[11px] text-slate-300 mt-2">
                          {n.what}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <div className="p-3 border-t border-slate-800/60 font-mono2 text-[10px] text-slate-500 tracking-widest">
        DATAFLOW · Business steers → Decision proposes → Execution acts →
        Knowledge grounds → Infrastructure logs everything
      </div>
    </div>
  );
}
