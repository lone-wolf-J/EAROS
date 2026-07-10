import React from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function ExecutiveCopilot() {
  const { data: health } = useSWR("/intelligence/organization/health", fetcher);
  const { data: gaps } = useSWR("/intelligence/workforce/skill-gaps", fetcher);
  const { data: strategy } = useSWR("/intelligence/strategy", fetcher);

  return (
    <AppLayout>
      <div data-testid={EAROS.executiveRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            EXECUTIVE COPILOT
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Workforce Intelligence
          </h1>
          <div className="text-slate-500 text-sm">
            Organizational health · skill gaps · strategy — all explainable, all
            grounded in world state.
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            ["DEPARTMENTS", health?.total_departments],
            ["TEAMS", health?.total_teams],
            ["OPEN REQS", health?.total_open_reqs],
            ["AVG ATTRITION", `${((health?.avg_attrition || 0) * 100).toFixed(1)}%`],
            ["AVG HEALTH", `${Math.round((health?.avg_health_score || 0) * 100)}`],
          ].map(([k, v]) => (
            <div key={k} className="p-4 border border-slate-800 bg-slate-900 rounded-md">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                {k}
              </div>
              <div className="mt-2 font-display font-black text-2xl text-slate-50">
                {v ?? "—"}
              </div>
            </div>
          ))}
        </div>

        {/* Strategy AI card */}
        {strategy && (
          <div data-testid={EAROS.strategyCard}>
            <AIDecisionCard rec={strategy} />
          </div>
        )}

        {/* Org Health table */}
        <div
          data-testid={EAROS.orgHealthTable}
          className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden"
        >
          <div className="p-4 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
            ORGANIZATIONAL HEALTH · BY DEPARTMENT
          </div>
          <table className="w-full text-[12px]">
            <thead className="bg-slate-950 text-slate-500 font-mono2">
              <tr>
                <th className="text-left px-4 py-2">DEPARTMENT</th>
                <th className="text-right px-4 py-2">HEADCOUNT</th>
                <th className="text-right px-4 py-2">OPEN SEATS</th>
                <th className="text-right px-4 py-2">ATTRITION</th>
                <th className="text-right px-4 py-2">HEALTH</th>
                <th className="text-right px-4 py-2">TEAMS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {Object.entries(health?.by_department || {}).map(([name, d]) => (
                <tr key={name} className="hover:bg-slate-800/40">
                  <td className="px-4 py-2 text-slate-200">{name}</td>
                  <td className="px-4 py-2 text-right font-mono2">{d.headcount}</td>
                  <td className="px-4 py-2 text-right font-mono2">{d.open_seats}</td>
                  <td className="px-4 py-2 text-right font-mono2">
                    {(d.attrition_rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-2 text-right font-mono2">
                    <span
                      className={`px-1.5 py-0.5 rounded-sm border text-[10px] ${
                        d.health_score >= 0.8
                          ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                          : d.health_score >= 0.7
                            ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                            : "text-rose-400 border-rose-500/30 bg-rose-500/10"
                      }`}
                    >
                      {Math.round(d.health_score * 100)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono2">{d.teams}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Skill gap */}
        <div
          data-testid={EAROS.skillGapTable}
          className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden"
        >
          <div className="p-4 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
            WORKFORCE INTELLIGENCE · SKILL DEMAND vs SUPPLY
          </div>
          <table className="w-full text-[12px]">
            <thead className="bg-slate-950 text-slate-500 font-mono2">
              <tr>
                <th className="text-left px-4 py-2">SKILL</th>
                <th className="text-right px-4 py-2">DEMAND (OPEN REQS)</th>
                <th className="text-right px-4 py-2">SUPPLY (CANDIDATES)</th>
                <th className="text-right px-4 py-2">GAP</th>
                <th className="text-right px-4 py-2">SCARCITY</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {gaps?.slice(0, 15).map((g) => (
                <tr key={g.skill} className="hover:bg-slate-800/40">
                  <td className="px-4 py-2 text-slate-200 capitalize">
                    {g.skill}
                  </td>
                  <td className="px-4 py-2 text-right font-mono2">{g.demand}</td>
                  <td className="px-4 py-2 text-right font-mono2">{g.supply}</td>
                  <td
                    className={`px-4 py-2 text-right font-mono2 ${
                      g.gap > 0 ? "text-rose-400" : "text-emerald-400"
                    }`}
                  >
                    {g.gap > 0 ? `+${g.gap}` : g.gap}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span
                      className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] uppercase ${
                        g.scarcity === "critical"
                          ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
                          : g.scarcity === "high"
                            ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
                            : "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                      }`}
                    >
                      {g.scarcity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}
