import React, { useState } from "react";
import useSWR from "swr";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const STAGE_ORDER = [
  "sourced",
  "screening",
  "phone_screen",
  "technical",
  "onsite",
  "offer",
  "hired",
];
const STAGE_COLORS = {
  sourced: "#6366f1",
  screening: "#8b5cf6",
  phone_screen: "#a855f7",
  technical: "#22d3ee",
  onsite: "#f59e0b",
  offer: "#10b981",
  hired: "#34d399",
  rejected: "#64748b",
  withdrawn: "#475569",
};

function Kpi({ label, value, sub, testId, loading, onClick }) {
  const Wrap = onClick ? "button" : "div";
  return (
    <Wrap
      data-testid={testId}
      onClick={onClick}
      className={`p-4 border rounded-md text-left transition ${
        onClick
          ? "border-slate-800 bg-slate-900 hover:border-indigo-500/60 hover:bg-slate-900/60 cursor-pointer"
          : "border-slate-800 bg-slate-900"
      }`}
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
        {label}
      </div>
      {loading ? (
        <>
          <div className="mt-2 h-8 w-16 bg-slate-800 rounded-sm animate-pulse" />
          <div className="mt-2 h-3 w-24 bg-slate-800/60 rounded-sm animate-pulse" />
        </>
      ) : (
        <>
          <div className="mt-2 font-display font-black text-3xl text-slate-50 tracking-tight leading-none">
            {value}
          </div>
          {sub && <div className="mt-2 text-slate-400 text-[12px]">{sub}</div>}
          {onClick && (
            <div className="mt-2 font-mono2 text-[10px] tracking-widest text-indigo-400">
              CLICK TO DRILL DOWN →
            </div>
          )}
        </>
      )}
    </Wrap>
  );
}

export default function HiringDashboard() {
  const { data } = useSWR("/apps/dashboard/summary", fetcher);
  const { data: strategy } = useSWR("/intelligence/strategy", fetcher);
  const [drill, setDrill] = useState(null); // "open_reqs" | "in_pipeline" | "offers_active" | "hired_ytd" | "ttf" | "p0"

  const stageData = STAGE_ORDER.map((s) => ({
    stage: s,
    count: data?.pipeline_by_stage?.[s] || 0,
  }));
  const countryData = Object.entries(data?.reqs_by_country || {}).map(
    ([name, value]) => ({ name, value }),
  );
  const priorityData = Object.entries(data?.reqs_by_priority || {}).map(
    ([name, value]) => ({ name, value }),
  );

  return (
    <AppLayout>
      <div data-testid={EAROS.dashboardRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            HIRING DASHBOARD · LEVELSHIFT
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            {data?.organization?.name || "LevelShift"}
          </h1>
          <div className="text-slate-500 text-sm">
            {data?.organization?.industry} · {data?.organization?.headquarters}
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Kpi loading={!data}
            label="OPEN REQS"
            value={data?.kpis?.open_reqs ?? "—"}
            sub={`${data?.reqs_by_country?.India || 0} India · ${data?.reqs_by_country?.USA || 0} USA`}
            testId={EAROS.kpiCard("open_reqs")}
            onClick={() => setDrill("open_reqs")} />
          <Kpi loading={!data}
            label="IN PIPELINE"
            value={data?.kpis?.in_pipeline ?? "—"}
            sub={`${data?.kpis?.total_candidates ?? 0} total candidates`}
            testId={EAROS.kpiCard("in_pipeline")}
            onClick={() => setDrill("in_pipeline")} />
          <Kpi loading={!data}
            label="OFFERS ACTIVE"
            value={data?.kpis?.offers_active ?? "—"}
            testId={EAROS.kpiCard("offers_active")}
            onClick={() => setDrill("offers_active")} />
          <Kpi loading={!data}
            label="HIRED YTD"
            value={data?.kpis?.hired_ytd ?? "—"}
            testId={EAROS.kpiCard("hired_ytd")}
            onClick={() => setDrill("hired_ytd")} />
          <Kpi loading={!data}
            label="AVG TIME-TO-FILL"
            value={data ? `${data?.kpis?.avg_time_to_fill_days ?? "—"}d` : "—"}
            testId={EAROS.kpiCard("ttf")}
            onClick={() => setDrill("ttf")} />
          <Kpi loading={!data}
            label="P0 ROLES"
            value={data?.reqs_by_priority?.P0 ?? 0}
            sub="critical priority"
            testId={EAROS.kpiCard("p0")}
            onClick={() => setDrill("p0")} />
        </div>

        {drill && (
          <DrillDownDrawer kpi={drill} onClose={() => setDrill(null)} />
        )}

        {/* Pipeline + charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div
            data-testid={EAROS.pipelineStrip}
            className="lg:col-span-2 border border-slate-800 bg-slate-900 rounded-md"
          >
            <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
              <div>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                  PIPELINE BY STAGE
                </div>
                <div className="font-display text-lg font-bold text-slate-100">
                  {data?.kpis?.total_candidates || 0} candidates
                </div>
              </div>
            </div>
            <div className="h-64 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stageData} margin={{ left: 4, right: 8 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="2 4" vertical={false} />
                  <XAxis
                    dataKey="stage"
                    tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }}
                    axisLine={{ stroke: "#334155" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }}
                    axisLine={{ stroke: "#334155" }}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#020617",
                      border: "1px solid #334155",
                      fontFamily: "JetBrains Mono",
                      fontSize: 11,
                    }}
                  />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                    {stageData.map((s) => (
                      <Cell key={s.stage} fill={STAGE_COLORS[s.stage] || "#6366f1"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-slate-800 bg-slate-900 rounded-md">
            <div className="p-4 border-b border-slate-800/60">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                REQS BY COUNTRY
              </div>
            </div>
            <div className="h-64 p-2 flex items-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={countryData}
                    innerRadius={50}
                    outerRadius={80}
                    dataKey="value"
                    stroke="#020617"
                    label={{ fill: "#e2e8f0", fontFamily: "JetBrains Mono", fontSize: 11 }}
                  >
                    {countryData.map((c) => (
                      <Cell
                        key={c.name}
                        fill={c.name === "India" ? "#f59e0b" : "#6366f1"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#020617",
                      border: "1px solid #334155",
                      fontFamily: "JetBrains Mono",
                      fontSize: 11,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Priority + strategy */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="border border-slate-800 bg-slate-900 rounded-md">
            <div className="p-4 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
              REQS BY PRIORITY
            </div>
            <div className="p-4 space-y-2">
              {priorityData.map((p) => (
                <div key={p.name} className="flex items-center gap-3">
                  <span className="font-mono2 text-[11px] text-slate-500 w-6">
                    {p.name}
                  </span>
                  <div className="flex-1 h-2 bg-slate-800 rounded-sm overflow-hidden">
                    <div
                      className="h-full bg-indigo-500"
                      style={{
                        width: `${(p.value / (data?.kpis?.open_reqs || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="font-mono2 text-[12px] text-slate-200 w-6 text-right">
                    {p.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 border border-slate-800 bg-slate-900 rounded-md trace-beam">
            <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
              <div>
                <div className="font-mono2 text-[10px] tracking-widest text-indigo-400">
                  STRATEGY INTELLIGENCE
                </div>
                <div className="font-display text-base font-bold text-slate-100">
                  {strategy?.title || "Loading…"}
                </div>
              </div>
              <div className="font-mono2 text-[11px] text-slate-500">
                confidence · {Math.round((strategy?.confidence?.value || 0) * 100)}%
              </div>
            </div>
            <div className="p-4 space-y-2">
              <div className="text-slate-300 text-[13px]">{strategy?.summary}</div>
              <ol className="space-y-1 mt-2">
                {strategy?.reasoning?.map((r, i) => (
                  <li key={i} className="flex gap-2 text-[12px]">
                    <span className="font-mono2 text-indigo-400">
                      {String(r.step).padStart(2, "0")}
                    </span>
                    <span className="text-slate-300">{r.thought}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}


/* ============================================================
   Drill-down drawer — right-side panel with kpi-specific detail
   ============================================================ */

const DRILL_META = {
  open_reqs:      { title: "Open Requisitions",           subtitle: "Active reqs across LevelShift" },
  in_pipeline:    { title: "Candidates In Pipeline",      subtitle: "Sourced through onsite stages" },
  offers_active:  { title: "Active Offers",               subtitle: "Awaiting candidate signature" },
  hired_ytd:      { title: "Hired Year-to-Date",          subtitle: "Closed and signed" },
  ttf:            { title: "Time-to-Fill by Role",        subtitle: "Days open · sorted worst first" },
  p0:             { title: "P0 (Critical) Requisitions",  subtitle: "Board-level priority" },
};

function DrillDownDrawer({ kpi, onClose }) {
  const meta = DRILL_META[kpi] || { title: kpi, subtitle: "" };
  const navigate = useNavigate();

  const { data: jobs } = useSWR("/world/jobs", fetcher);
  // Only load candidates for pipeline/offer/hired drills — spare the payload
  const wantsCands = ["in_pipeline", "offers_active", "hired_ytd"].includes(kpi);
  const { data: cands } = useSWR(wantsCands ? "/world/candidates" : null, fetcher);

  let rows = [];
  if (kpi === "open_reqs") {
    rows = (jobs || []).filter((j) => j.status === "open");
  } else if (kpi === "p0") {
    rows = (jobs || []).filter((j) => j.priority === "P0");
  } else if (kpi === "ttf") {
    rows = [...(jobs || [])].sort(
      (a, b) => (b.opened_days_ago ?? 0) - (a.opened_days_ago ?? 0),
    );
  } else if (kpi === "in_pipeline") {
    rows = (cands || []).filter(
      (c) =>
        !["hired", "rejected", "withdrawn"].includes(c.stage),
    );
  } else if (kpi === "offers_active") {
    rows = (cands || []).filter((c) => c.stage === "offer");
  } else if (kpi === "hired_ytd") {
    rows = (cands || []).filter((c) => c.stage === "hired");
  }

  const loading = kpi === "open_reqs" || kpi === "p0" || kpi === "ttf"
    ? !jobs
    : !cands;

  return (
    <div
      data-testid="dashboard-drill-drawer"
      className="fixed inset-0 z-40 flex justify-end"
    >
      <div
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-2xl h-full bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
        <div className="px-5 py-3 border-b border-slate-800 flex items-start justify-between gap-3">
          <div>
            <div className="font-mono2 text-[10px] tracking-widest text-indigo-400">
              DRILL DOWN · {kpi.toUpperCase()}
            </div>
            <div className="font-display text-xl font-black text-slate-100">
              {meta.title}
            </div>
            <div className="text-[12px] text-slate-500">{meta.subtitle}</div>
          </div>
          <button
            data-testid="dashboard-drill-close"
            onClick={onClose}
            className="p-1.5 rounded-sm hover:bg-slate-800 text-slate-400"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-16 bg-slate-900/50 border border-slate-800 rounded-sm animate-pulse"
              />
            ))
          ) : rows.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-[13px]">
              No records in this segment.
            </div>
          ) : (
            rows.map((r, i) => {
              const isJob = "job_id" in r;
              return (
                <div
                  key={isJob ? r.job_id : r.candidate_id}
                  data-testid={`drill-row-${i}`}
                  className="p-3 border border-slate-800 bg-slate-900/50 rounded-sm hover:border-indigo-500/40 transition cursor-pointer"
                  onClick={() => {
                    if (isJob) navigate(`/recruiter?job=${r.job_id}`);
                    else navigate(`/recruiter?job=${r.job_id}`);
                    onClose();
                  }}
                >
                  {isJob ? (
                    <JobRow job={r} />
                  ) : (
                    <CandidateRow c={r} jobs={jobs || []} />
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className="px-5 py-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono2 text-slate-500">
          <span>{rows.length} record{rows.length === 1 ? "" : "s"}</span>
          <button
            data-testid="dashboard-drill-open-copilot"
            onClick={() => {
              navigate("/recruiter");
              onClose();
            }}
            className="px-3 py-1.5 rounded-sm border border-slate-700 hover:border-indigo-500/60 text-slate-300 hover:text-indigo-300"
          >
            open recruiter copilot →
          </button>
        </div>
      </div>
    </div>
  );
}

function JobRow({ job }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="text-slate-100 text-[13px] font-medium truncate">
          {job.title}
        </div>
        <div className="text-[11px] text-slate-500 truncate">
          {job.location} · {job.job_id} · opened {job.opened_days_ago ?? "?"}d ago
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span
          className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${
            job.priority === "P0"
              ? "text-rose-300 border-rose-500/40 bg-rose-500/10"
              : job.priority === "P1"
                ? "text-amber-300 border-amber-500/40 bg-amber-500/10"
                : "text-slate-400 border-slate-700"
          }`}
        >
          {job.priority}
        </span>
        <span className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border border-slate-700 text-slate-400">
          {job.level}
        </span>
      </div>
    </div>
  );
}

function CandidateRow({ c, jobs }) {
  const job = jobs.find((j) => j.job_id === c.job_id);
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="text-slate-100 text-[13px] font-medium truncate">
          {c.full_name}
        </div>
        <div className="text-[11px] text-slate-500 truncate">
          {c.current_title} · {c.location}
        </div>
        <div className="text-[11px] text-slate-500 truncate">
          {job ? job.title : c.job_id} · {c.candidate_id}
        </div>
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        <span
          className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border"
          style={{
            color: STAGE_COLORS[c.stage] || "#94a3b8",
            borderColor: (STAGE_COLORS[c.stage] || "#334155") + "60",
          }}
        >
          {c.stage}
        </span>
        {c.fit_score != null && (
          <span className="font-mono2 text-[10px] text-slate-400">
            fit · {Math.round(c.fit_score * 100)}%
          </span>
        )}
      </div>
    </div>
  );
}

