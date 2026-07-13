import React, { useEffect, useState } from "react";
import useSWR from "swr";
import {
  Line,
  LineChart as RechartsLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function ExecutiveCopilot() {
  const { data: health } = useSWR("/intelligence/organization/health", fetcher);
  const { data: gaps } = useSWR("/intelligence/workforce/skill-gaps", fetcher);
  const { data: strategy } = useSWR("/intelligence/strategy", fetcher);

  const [levers, setLevers] = useState({
    attrition_pct: 0.12,
    hiring_freeze: false,
    budget_delta_pct: 0.0,
    bangalore_expansion: false,
    ai_engineering_doubles: false,
    horizon_months: 12,
  });
  const [sim, setSim] = useState(null);

  const runSim = async (next) => {
    const payload = next || levers;
    const { data } = await api.post("/simulate/what-if", payload);
    setSim(data);
  };

  useEffect(() => {
    runSim(levers);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = (patch) => {
    const next = { ...levers, ...patch };
    setLevers(next);
    runSim(next);
  };

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
            Organizational health · skill gaps · strategy · what-if simulation.
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            ["DEPARTMENTS", health?.total_departments],
            ["TEAMS", health?.total_teams],
            ["OPEN REQS", health?.total_open_reqs],
            ["AVG ATTRITION", health ? `${((health.avg_attrition || 0) * 100).toFixed(1)}%` : null],
            ["AVG HEALTH", health ? Math.round((health.avg_health_score || 0) * 100) : null],
          ].map(([k, v]) => (
            <div key={k} className="p-4 border border-slate-800 bg-slate-900 rounded-md">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                {k}
              </div>
              {health ? (
                <div className="mt-2 font-display font-black text-2xl text-slate-50">
                  {v ?? "—"}
                </div>
              ) : (
                <div className="mt-2 h-7 w-14 bg-slate-800 rounded-sm animate-pulse" />
              )}
            </div>
          ))}
        </div>

        {/* What-If simulator */}
        <div className="border border-cyan-500/30 bg-cyan-500/5 rounded-md">
          <div className="p-4 border-b border-cyan-500/20 flex items-center gap-2">
            <div className="font-mono2 text-[10px] tracking-widest text-cyan-400">
              WHAT-IF SIMULATION · MOVE SLIDERS
            </div>
            {sim && (
              <span className="ml-auto font-mono2 text-[11px] text-slate-400">
                {sim.starting_headcount} → {sim.ending_headcount} in {levers.horizon_months} months
                <span className={sim.net_change >= 0 ? "text-emerald-400 ml-1" : "text-rose-400 ml-1"}>
                  ({sim.net_change >= 0 ? "+" : ""}{sim.net_change})
                </span>
              </span>
            )}
          </div>
          <div className="p-4 grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4">
            <div className="space-y-4">
              <div>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                  ATTRITION · {Math.round(levers.attrition_pct * 100)}%
                </div>
                <input
                  data-testid={EAROS.simulateAttritionSlider}
                  type="range" min="0" max="30" value={levers.attrition_pct * 100}
                  onChange={(e) => update({ attrition_pct: Number(e.target.value) / 100 })}
                  className="w-full accent-cyan-500"
                />
              </div>
              <div>
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                  BUDGET DELTA · {levers.budget_delta_pct >= 0 ? "+" : ""}
                  {Math.round(levers.budget_delta_pct * 100)}%
                </div>
                <input
                  data-testid={EAROS.simulateBudget}
                  type="range" min="-30" max="30" value={levers.budget_delta_pct * 100}
                  onChange={(e) => update({ budget_delta_pct: Number(e.target.value) / 100 })}
                  className="w-full accent-cyan-500"
                />
              </div>
              <label className="flex items-center gap-2 text-[12px] text-slate-300">
                <input
                  data-testid={EAROS.simulateHiringFreeze}
                  type="checkbox" checked={levers.hiring_freeze}
                  onChange={(e) => update({ hiring_freeze: e.target.checked })}
                  className="accent-rose-500"
                />
                Hiring freeze
              </label>
              <label className="flex items-center gap-2 text-[12px] text-slate-300">
                <input
                  data-testid={EAROS.simulateBangalore}
                  type="checkbox" checked={levers.bangalore_expansion}
                  onChange={(e) => update({ bangalore_expansion: e.target.checked })}
                  className="accent-emerald-500"
                />
                Bangalore expansion
              </label>
              <label className="flex items-center gap-2 text-[12px] text-slate-300">
                <input
                  data-testid={EAROS.simulateAiDoubles}
                  type="checkbox" checked={levers.ai_engineering_doubles}
                  onChange={(e) => update({ ai_engineering_doubles: e.target.checked })}
                  className="accent-violet-500"
                />
                AI engineering doubles
              </label>
            </div>
            <div className="h-72 bg-slate-950 border border-slate-800 rounded-sm p-2">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsLine data={sim?.trajectory || []}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="2 4" vertical={false} />
                  <XAxis dataKey="month"
                          tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }}
                          axisLine={{ stroke: "#334155" }} tickLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }}
                          axisLine={{ stroke: "#334155" }} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#020617", border: "1px solid #334155",
                                            fontFamily: "JetBrains Mono", fontSize: 11 }} />
                  <Line type="monotone" dataKey="headcount" stroke="#22d3ee" strokeWidth={2}
                        dot={{ fill: "#22d3ee", r: 3 }} />
                </RechartsLine>
              </ResponsiveContainer>
            </div>
          </div>
          {sim?.recommendation && (
            <div className="border-t border-cyan-500/20 p-4">
              <AIDecisionCard rec={sim.recommendation} />
            </div>
          )}
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
