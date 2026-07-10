import React, { useMemo } from "react";
import useSWR from "swr";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  BadgeDollarSign,
  Boxes,
  ClipboardCheck,
  Cpu,
  FileText,
  GitBranch,
  Headphones,
  LineChart,
  MessageSquare,
  Mic,
  Radar,
  Radio,
  Rocket,
  ScanSearch,
  ScrollText,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trophy,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const ICON_MAP = {
  MessageSquare, FileText, LineChart, Radar, ScrollText, Trophy, Send, Radio,
  ClipboardCheck, Mic, BadgeDollarSign, ShieldCheck, ScanSearch, GitBranch, Cpu,
  ShieldAlert, Sparkles,
};
const COLOR_MAP = {
  indigo: {
    text: "text-indigo-300", bg: "bg-indigo-500/10", border: "border-indigo-500/30",
    dot: "bg-indigo-400",
  },
  emerald: {
    text: "text-emerald-300", bg: "bg-emerald-500/10", border: "border-emerald-500/30",
    dot: "bg-emerald-400",
  },
  amber: {
    text: "text-amber-300", bg: "bg-amber-500/10", border: "border-amber-500/30",
    dot: "bg-amber-400",
  },
  cyan: {
    text: "text-cyan-300", bg: "bg-cyan-500/10", border: "border-cyan-500/30",
    dot: "bg-cyan-400",
  },
  violet: {
    text: "text-violet-300", bg: "bg-violet-500/10", border: "border-violet-500/30",
    dot: "bg-violet-400",
  },
  rose: {
    text: "text-rose-300", bg: "bg-rose-500/10", border: "border-rose-500/30",
    dot: "bg-rose-400",
  },
};

const fetcher = (url) => api.get(url).then((r) => r.data);

function humanEvent(e) {
  const map = {
    "runtime.execution.started": ["started", "runtime"],
    "runtime.execution.completed": ["completed", "runtime"],
    "runtime.execution.failed": ["failed", "runtime"],
    "runtime.step.started": ["step started", "capability"],
    "runtime.step.completed": ["step completed", "capability"],
    "policy.evaluated": ["policy passed", "policy engine"],
    "policy.violated": ["policy blocked", "policy engine"],
    "governance.approval.requested": ["approval requested", "governance"],
    "governance.approval.granted": ["approval granted", "governance"],
    "governance.approval.denied": ["approval denied", "governance"],
    "reflection.created": ["reflection recorded", "reflection agent"],
    "world.candidate.stage_changed": ["candidate advanced", "world"],
  };
  const [verb, actor] = map[e.event_type] || [e.event_type, "system"];
  const subject = e.subject_id ? ` · ${e.subject_id}` : "";
  return { verb, actor, subject, time: e.occurred_at?.slice(11, 19) };
}

function MissionKPI({ label, value, sub, tone = "indigo", testId }) {
  const c = COLOR_MAP[tone] || COLOR_MAP.indigo;
  return (
    <div
      data-testid={testId}
      className={`p-3 border ${c.border} bg-slate-900 rounded-md relative overflow-hidden`}
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
        {label}
      </div>
      <div className={`mt-1 font-display font-black text-2xl leading-none ${c.text}`}>
        {value}
      </div>
      {sub && <div className="mt-1.5 text-slate-500 text-[11px]">{sub}</div>}
      <div className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${c.dot} animate-pulse`} />
    </div>
  );
}

export default function MissionControl() {
  const { data, mutate } = useSWR("/mission/snapshot", fetcher, {
    refreshInterval: 3000,
  });
  const navigate = useNavigate();

  const c = data?.counts || {};

  const pulseByCategory = useMemo(() => {
    const groups = {};
    for (const a of data?.agent_pulse || []) {
      (groups[a.category] = groups[a.category] || []).push(a);
    }
    return groups;
  }, [data]);

  return (
    <AppLayout>
      <div data-testid={EAROS.missionRoot} className="p-6 space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
              <span className="pulse-dot" /> MISSION CONTROL · LIVE
              <span className="text-slate-600">
                · updated {data?.as_of?.slice(11, 19) || "…"}
              </span>
            </div>
            <h1 className="font-display text-3xl font-black tracking-tight">
              An operating system, not a dashboard.
            </h1>
            <div className="text-slate-500 text-sm">
              Every active execution, every agent thinking, every policy
              evaluated. Watch EAROS orchestrate.
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate("/scenarios")}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2"
            >
              <Rocket className="w-3.5 h-3.5" strokeWidth={1.5} />
              RUN A DEMO SCENARIO
            </button>
            <button
              onClick={() => navigate("/intake")}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2"
            >
              <MessageSquare className="w-3.5 h-3.5" strokeWidth={1.5} />
              START HIRING INTAKE
            </button>
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          <MissionKPI label="EVENTS" value={c.events_total ?? "—"}
                       sub="immutable log" tone="indigo"
                       testId={EAROS.missionKpi("events")} />
          <MissionKPI label="EXECUTIONS" value={c.executions_total ?? "—"}
                       sub={`${c.executions_running || 0} in flight`}
                       tone="cyan" testId={EAROS.missionKpi("executions")} />
          <MissionKPI label="APPROVALS" value={c.approvals_pending ?? "—"}
                       sub="human-required" tone="amber"
                       testId={EAROS.missionKpi("approvals")} />
          <MissionKPI label="POLICIES" value={c.policies_active ?? "—"}
                       sub="active" tone="rose"
                       testId={EAROS.missionKpi("policies")} />
          <MissionKPI label="REFLECTIONS" value={c.reflections_total ?? "—"}
                       sub="lessons banked" tone="violet"
                       testId={EAROS.missionKpi("reflections")} />
          <MissionKPI label="OPEN REQS" value={c.open_reqs ?? "—"}
                       sub="India + USA" tone="emerald"
                       testId={EAROS.missionKpi("open_reqs")} />
          <MissionKPI label="CANDIDATES" value={c.candidates_total ?? "—"}
                       sub="in world state" tone="cyan"
                       testId={EAROS.missionKpi("candidates")} />
          <MissionKPI label="AGENTS" value={data?.agent_pulse?.length ?? "—"}
                       sub="online" tone="indigo"
                       testId={EAROS.missionKpi("agents")} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: agents grid */}
          <div className="lg:col-span-2 border border-slate-800 bg-slate-900 rounded-md">
            <div className="p-3 border-b border-slate-800/60 flex items-center justify-between">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                AGENT ACTIVITY · LAST 60 SECONDS
              </div>
              <NavLink to="/agents"
                       className="font-mono2 text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
                agent registry <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
              </NavLink>
            </div>
            <div className="p-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
              {(data?.agent_pulse || []).map((a) => {
                const Icon = ICON_MAP[a.icon] || Cpu;
                const col = COLOR_MAP[a.color] || COLOR_MAP.indigo;
                const inFlight = a.in_flight > 0;
                return (
                  <div
                    key={a.agent_id}
                    data-testid={EAROS.agentPulseCard(a.agent_id)}
                    className={`border ${col.border} rounded-sm p-2.5 bg-slate-950/60 relative overflow-hidden`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-3.5 h-3.5 ${col.text}`} strokeWidth={1.5} />
                      <div className="text-slate-100 text-[12px] font-medium flex-1 truncate">
                        {a.name}
                      </div>
                      {inFlight && (
                        <span className="flex items-center gap-1 font-mono2 text-[10px] text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          {a.in_flight}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-[10px] font-mono2 text-slate-400">
                      <div>
                        <div className="text-slate-500">24h</div>
                        <div className="text-slate-200">{a.executions_24h}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">latency</div>
                        <div className="text-slate-200">{a.avg_latency_ms}ms</div>
                      </div>
                      <div>
                        <div className="text-slate-500">health</div>
                        <div className={
                          a.health === "healthy"
                            ? "text-emerald-400" : "text-amber-400"}>
                          {a.health}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: approvals + running exec */}
          <div className="space-y-4">
            <div className="border border-amber-500/30 bg-amber-500/5 rounded-md">
              <div className="p-3 border-b border-amber-500/20 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" strokeWidth={1.5} />
                <div className="font-mono2 text-[10px] tracking-widest text-amber-400">
                  HUMAN ACCOUNTABILITY QUEUE
                </div>
                <span className="ml-auto font-mono2 text-[11px] text-amber-400">
                  {data?.pending_approvals?.length || 0} pending
                </span>
              </div>
              <div className="divide-y divide-amber-500/10 max-h-56 overflow-y-auto">
                {data?.pending_approvals?.length ? data.pending_approvals.map((a) => (
                  <div
                    key={a.approval_id}
                    data-testid={EAROS.approvalMission(a.approval_id)}
                    className="p-3 text-[12px]"
                  >
                    <div className="text-slate-100 truncate">{a.reason}</div>
                    <div className="mt-1 flex items-center justify-between font-mono2 text-[10px] text-slate-500">
                      <span>{a.subject_type} · {a.subject_id}</span>
                      <NavLink to="/governance"
                               className="text-amber-400 hover:text-amber-300 flex items-center gap-1">
                        review <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
                      </NavLink>
                    </div>
                  </div>
                )) : (
                  <div className="p-4 text-slate-500 text-[12px] text-center">
                    No pending approvals.
                  </div>
                )}
              </div>
            </div>

            <div className="border border-slate-800 bg-slate-900 rounded-md">
              <div className="p-3 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5" strokeWidth={1.5} />
                RUNTIME · IN-FLIGHT + RECENT
              </div>
              <div className="divide-y divide-slate-800/60 max-h-64 overflow-y-auto">
                {[...(data?.running_executions || []),
                  ...(data?.recent_executions || [])
                    .filter((e) => !(data?.running_executions || [])
                      .find((r) => r.execution_id === e.execution_id))
                    .slice(0, 5)]
                  .slice(0, 8).map((ex) => {
                    const status = ex.status;
                    const tint = {
                      running: "text-cyan-400 border-cyan-500/30",
                      awaiting_approval: "text-amber-400 border-amber-500/30",
                      succeeded: "text-emerald-400 border-emerald-500/30",
                      failed: "text-rose-400 border-rose-500/30",
                      policy_blocked: "text-rose-400 border-rose-500/30",
                    }[status] || "text-slate-400 border-slate-500/30";
                    return (
                      <div
                        key={ex.execution_id}
                        data-testid={EAROS.runningExecutionCard(ex.execution_id)}
                        className="p-3"
                      >
                        <div className="flex items-center gap-2 text-[12px]">
                          <span className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${tint}`}>
                            {status?.replace("_", " ").toUpperCase()}
                          </span>
                          <span className="text-slate-100 truncate flex-1">{ex.goal}</span>
                        </div>
                        <div className="mt-1 font-mono2 text-[10px] text-slate-500">
                          {ex.steps?.length || 0} step(s) · {ex.started_at?.slice(11, 19)}
                        </div>
                      </div>
                    );
                  })}
                {!(data?.running_executions?.length || data?.recent_executions?.length) && (
                  <div className="p-4 text-slate-500 text-[12px] text-center">
                    No recent runtime activity.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Ambient ticker + events + reflections */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div
            data-testid={EAROS.ambientTicker}
            className="lg:col-span-2 border border-slate-800 bg-slate-900 rounded-md"
          >
            <div className="p-3 border-b border-slate-800/60 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400" strokeWidth={1.5} />
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                AGENT ACTIVITY STREAM
              </div>
              <span className="ml-auto flex items-center gap-1 font-mono2 text-[10px] text-emerald-400">
                <span className="pulse-dot" /> live
              </span>
            </div>
            <div className="divide-y divide-slate-800/40 max-h-72 overflow-y-auto">
              {(data?.ambient_activity || []).map((a, i) => {
                const col = COLOR_MAP[
                  {
                    "agent.sourcing": "cyan", "agent.resume_intelligence": "cyan",
                    "agent.ranking": "cyan", "agent.outreach": "emerald",
                    "agent.response_monitor": "emerald",
                    "agent.market_intelligence": "violet",
                    "agent.policy": "rose", "agent.reflection": "violet",
                    "agent.screening": "amber",
                  }[a.agent_id] || "indigo"
                ];
                return (
                  <div key={i} className="p-2.5 grid grid-cols-[64px_180px_1fr_120px] gap-3 text-[12px]">
                    <span className="font-mono2 text-slate-500">
                      {a.occurred_at?.slice(11, 19)}
                    </span>
                    <span className={`font-mono2 ${col.text}`}>{a.agent_id}</span>
                    <span className="text-slate-200 truncate">{a.message}</span>
                    <span className="text-right font-mono2 text-slate-500">
                      {a.latency_ms}ms · {(a.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                );
              })}
              {(data?.recent_events || []).slice(0, 12).map((e) => {
                const h = humanEvent(e);
                return (
                  <div key={e.event_id} className="p-2.5 grid grid-cols-[64px_180px_1fr_120px] gap-3 text-[12px] bg-slate-950/40">
                    <span className="font-mono2 text-slate-500">{h.time}</span>
                    <span className="font-mono2 text-indigo-400">{h.actor}</span>
                    <span className="text-slate-300 truncate">
                      {h.verb}
                      <span className="text-slate-500">{h.subject}</span>
                    </span>
                    <span className="text-right font-mono2 text-slate-500">runtime</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="border border-violet-500/30 bg-violet-500/5 rounded-md">
            <div className="p-3 border-b border-violet-500/20 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" strokeWidth={1.5} />
              <div className="font-mono2 text-[10px] tracking-widest text-violet-400">
                RECENT REFLECTIONS
              </div>
              <NavLink to="/reflection"
                       className="ml-auto font-mono2 text-[11px] text-violet-400 hover:text-violet-300 flex items-center gap-1">
                all reflections <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
              </NavLink>
            </div>
            <div className="divide-y divide-violet-500/10 max-h-72 overflow-y-auto">
              {(data?.recent_reflections || []).map((r) => (
                <div key={r.reflection_id} className="p-3 text-[12px]">
                  <div className="text-slate-100 line-clamp-2">{r.what_happened}</div>
                  {r.improvements?.[0] && (
                    <div className="mt-1 flex items-start gap-1 text-violet-300 text-[11px]">
                      <Zap className="w-3 h-3 mt-0.5 shrink-0" strokeWidth={1.5} />
                      <span>{r.improvements[0]}</span>
                    </div>
                  )}
                  <div className="mt-1 font-mono2 text-[10px] text-slate-500">
                    {r.created_at?.slice(0, 19)}
                  </div>
                </div>
              ))}
              {!data?.recent_reflections?.length && (
                <div className="p-4 text-slate-500 text-[12px] text-center">
                  No reflections yet — run a scenario.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
