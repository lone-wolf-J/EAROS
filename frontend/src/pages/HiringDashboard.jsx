import React from "react";
import useSWR from "swr";
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

function Kpi({ label, value, sub, testId }) {
  return (
    <div
      data-testid={testId}
      className="p-4 border border-slate-800 bg-slate-900 rounded-md"
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
        {label}
      </div>
      <div className="mt-2 font-display font-black text-3xl text-slate-50 tracking-tight leading-none">
        {value}
      </div>
      {sub && <div className="mt-2 text-slate-400 text-[12px]">{sub}</div>}
    </div>
  );
}

export default function HiringDashboard() {
  const { data } = useSWR("/apps/dashboard/summary", fetcher);
  const { data: strategy } = useSWR("/intelligence/strategy", fetcher);

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
          <Kpi
            label="OPEN REQS"
            value={data?.kpis?.open_reqs ?? "—"}
            sub={`${data?.reqs_by_country?.India || 0} India · ${data?.reqs_by_country?.USA || 0} USA`}
            testId={EAROS.kpiCard("open_reqs")}
          />
          <Kpi
            label="IN PIPELINE"
            value={data?.kpis?.in_pipeline ?? "—"}
            sub={`${data?.kpis?.total_candidates ?? 0} total candidates`}
            testId={EAROS.kpiCard("in_pipeline")}
          />
          <Kpi
            label="OFFERS ACTIVE"
            value={data?.kpis?.offers_active ?? "—"}
            testId={EAROS.kpiCard("offers_active")}
          />
          <Kpi
            label="HIRED YTD"
            value={data?.kpis?.hired_ytd ?? "—"}
            testId={EAROS.kpiCard("hired_ytd")}
          />
          <Kpi
            label="AVG TIME-TO-FILL"
            value={`${data?.kpis?.avg_time_to_fill_days ?? "—"}d`}
            testId={EAROS.kpiCard("ttf")}
          />
          <Kpi
            label="P0 ROLES"
            value={data?.reqs_by_priority?.P0 ?? 0}
            sub="critical priority"
            testId={EAROS.kpiCard("p0")}
          />
        </div>

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
