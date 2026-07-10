import React, { useState } from "react";
import useSWR from "swr";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Rocket, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const LIFECYCLE_STAGES = [
  "Intake",
  "JD Intelligence",
  "Market Intelligence",
  "Planner",
  "Policy Evaluation",
  "Sourcing",
  "Resume Intelligence",
  "Ranking",
  "Outreach",
  "Response Monitor",
  "Screening",
  "Interview Intelligence",
  "Offer Intelligence",
  "Approval",
  "Reflection",
];

export default function Scenarios() {
  const { data: scenarios } = useSWR("/scenarios", fetcher);
  const [running, setRunning] = useState(null);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState({});
  const navigate = useNavigate();

  const run = async (scenario) => {
    setRunning(scenario.scenario_id);
    setProgress(0);
    // Animate stage progress locally while the backend runs the lifecycle.
    const interval = setInterval(() => {
      setProgress((p) => Math.min(LIFECYCLE_STAGES.length - 1, p + 1));
    }, 550);
    try {
      const { data } = await api.post(`/scenarios/${scenario.scenario_id}/run`);
      setResults((prev) => ({ ...prev, [scenario.scenario_id]: data }));
    } catch (e) {
      setResults((prev) => ({
        ...prev,
        [scenario.scenario_id]: { error: String(e) },
      }));
    } finally {
      clearInterval(interval);
      setProgress(LIFECYCLE_STAGES.length - 1);
      setTimeout(() => setRunning(null), 600);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.scenariosRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            DEMO SCENARIOS
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Watch a hire happen, end to end.
          </h1>
          <div className="text-slate-500 text-sm">
            Each scenario runs a complete lifecycle through the EAROS
            architecture — intake, sourcing, screening, outreach, interviewing,
            offer, and reflection — with every step gated by policy and
            recorded as immutable events.
          </div>
        </div>

        {/* Progress ribbon */}
        {running && (
          <div className="border border-cyan-500/40 bg-cyan-500/5 rounded-md p-4">
            <div className="font-mono2 text-[10px] tracking-widest text-cyan-400 mb-2 flex items-center gap-2">
              <span className="pulse-dot" /> RUNNING SCENARIO · {running}
            </div>
            <div className="flex items-center gap-1 overflow-x-auto">
              {LIFECYCLE_STAGES.map((s, i) => {
                const state = i < progress ? "done" : i === progress ? "active" : "pending";
                return (
                  <React.Fragment key={s}>
                    <div
                      className={`shrink-0 flex items-center gap-1 px-2 py-1 rounded-sm border font-mono2 text-[10px] ${
                        state === "done"
                          ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                          : state === "active"
                            ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-300 animate-pulse"
                            : "bg-slate-900 border-slate-800 text-slate-500"
                      }`}
                    >
                      {state === "done" && <CheckCircle2 className="w-3 h-3" strokeWidth={1.5} />}
                      {s}
                    </div>
                    {i < LIFECYCLE_STAGES.length - 1 && (
                      <span className="text-slate-700 font-mono2 shrink-0">→</span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        )}

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {scenarios?.map((s) => {
            const result = results[s.scenario_id];
            const isRunning = running === s.scenario_id;
            return (
              <div
                key={s.scenario_id}
                data-testid={EAROS.scenarioCard(s.scenario_id)}
                className="border border-slate-800 bg-slate-900 rounded-md p-5 relative overflow-hidden"
              >
                {isRunning && (
                  <div className="absolute inset-x-0 top-0 h-0.5 bg-cyan-400 animate-pulse" />
                )}
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-1">
                      {s.scenario_id}
                    </div>
                    <h3 className="font-display text-lg font-bold text-slate-100">
                      {s.title}
                    </h3>
                    <div className="text-slate-400 text-[13px] mt-1">
                      {s.tagline}
                    </div>
                  </div>
                </div>
                <div className="mt-3 p-3 bg-slate-950 border border-slate-800 rounded-sm text-[12px] text-slate-300 italic">
                  &ldquo;{s.brief}&rdquo;
                </div>

                <div className="mt-3 flex items-center justify-between gap-2">
                  <button
                    data-testid={EAROS.scenarioRunBtn(s.scenario_id)}
                    onClick={() => run(s)}
                    disabled={!!running}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2 disabled:opacity-40"
                  >
                    <Rocket className="w-3.5 h-3.5" strokeWidth={1.5} />
                    {isRunning ? "RUNNING…" : "RUN SCENARIO"}
                  </button>

                  {result && !result.error && (
                    <button
                      onClick={() => navigate("/governance")}
                      className="font-mono2 text-[11px] text-indigo-400 hover:text-indigo-300"
                    >
                      view audit →
                    </button>
                  )}
                </div>

                {result && !result.error && (
                  <div className="mt-3 border-t border-slate-800/60 pt-3">
                    <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-1">
                      LIFECYCLE COMPLETE
                    </div>
                    <div className="text-[12px] text-slate-300">
                      Sourcing sweep → screened {result.candidates_screened?.length || 0} candidates →
                      drafted outreach → scheduled interview → offer gated to
                      human approval → reflection recorded.
                    </div>
                    <div className="mt-1 font-mono2 text-[10px] text-slate-500">
                      correlation · {result.correlation_id}
                    </div>
                  </div>
                )}
                {result && result.error && (
                  <div className="mt-3 border-t border-slate-800/60 pt-3">
                    <div className="text-rose-400 text-[12px] flex items-center gap-1">
                      <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                      {result.error}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
