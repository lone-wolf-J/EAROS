import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { Radar, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function Sourcing() {
  const { data: jobs } = useSWR("/world/jobs", fetcher);
  const [jobId, setJobId] = useState(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({});
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (jobs && !jobId) setJobId(jobs[0]?.job_id);
  }, [jobs, jobId]);

  const run = async () => {
    if (!jobId) return;
    setRunning(true);
    setResult(null);
    setProgress({});
    const { data } = await api.get(`/sourcing/sweep/${jobId}`);
    // stagger channel reveal for a "live" feel
    for (const c of data.channels) {
      await new Promise((r) => setTimeout(r, 220));
      setProgress((p) => ({ ...p, [c.channel]: true }));
    }
    setResult(data);
    setRunning(false);
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.sourcingRoot} className="p-6 space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
              <Radar className="w-3.5 h-3.5" strokeWidth={1.5} />
              SOURCING · MULTI-SOURCE SWEEP
            </div>
            <h1 className="font-display text-3xl font-black tracking-tight">
              10 systems, one AI, one candidate list.
            </h1>
            <div className="text-slate-500 text-sm">
              Watch EAROS query LinkedIn, Dice, GitHub, Naukri, Internal ATS,
              Referrals, Community, Stack Overflow, Monster and Indeed in
              parallel — then deduplicate, rank, and confidence-score.
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={jobId || ""}
              onChange={(e) => setJobId(e.target.value)}
              className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              {jobs?.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.title} · {j.location}
                </option>
              ))}
            </select>
            <button
              data-testid={EAROS.sourcingRunBtn}
              onClick={run}
              disabled={running}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
            >
              <Zap className="w-3.5 h-3.5" strokeWidth={1.5} />
              {running ? "SWEEPING…" : "RUN SWEEP"}
            </button>
          </div>
        </div>

        {result && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              ["TOTAL MATCHES", result.total_matches, "indigo"],
              ["UNIQUE CANDIDATES", result.unique_matches, "emerald"],
              ["DUPLICATES REMOVED", result.duplicates_removed, "amber"],
              ["WEIGHTED QUALITY", `${Math.round(result.weighted_quality * 100)}`, "violet"],
            ].map(([label, val]) => (
              <div key={label} className="p-4 border border-slate-800 bg-slate-900 rounded-md">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                  {label}
                </div>
                <div className="mt-1 font-display font-black text-2xl text-slate-50">
                  {val?.toLocaleString?.() || val}
                </div>
              </div>
            ))}
          </div>
        )}

        {(running || result) && (
          <div className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden">
            <div className="p-3 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2">
              CHANNEL BREAKDOWN
              {running && (
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="pulse-dot" /> agent.sourcing · running
                </span>
              )}
            </div>
            <table className="w-full text-[12px]">
              <thead className="bg-slate-950 text-slate-500 font-mono2">
                <tr>
                  <th className="text-left px-4 py-2">CHANNEL</th>
                  <th className="text-right px-4 py-2">MATCHES</th>
                  <th className="text-right px-4 py-2">UNIQUE</th>
                  <th className="text-right px-4 py-2">DUPS</th>
                  <th className="text-right px-4 py-2">QUALITY</th>
                  <th className="text-right px-4 py-2">RESP PROB</th>
                  <th className="text-right px-4 py-2">LATENCY</th>
                  <th className="text-right px-4 py-2">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {(result?.channels || []).map((c) => {
                  const done = !!progress[c.channel] || !running;
                  return (
                    <tr key={c.channel} className={done ? "" : "opacity-40"}>
                      <td className="px-4 py-2 text-slate-200">{c.channel}</td>
                      <td className="px-4 py-2 text-right font-mono2">{c.matches}</td>
                      <td className="px-4 py-2 text-right font-mono2 text-emerald-400">
                        {c.unique_matches}
                      </td>
                      <td className="px-4 py-2 text-right font-mono2 text-amber-400">
                        {c.duplicates_removed}
                      </td>
                      <td className="px-4 py-2 text-right font-mono2">
                        {Math.round(c.quality_score * 100)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono2">
                        {Math.round(c.estimated_response_probability * 100)}%
                      </td>
                      <td className="px-4 py-2 text-right font-mono2 text-slate-500">
                        {c.latency_ms}ms
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className="px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                          {done ? "OK" : "…"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
