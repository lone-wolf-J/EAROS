import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Cpu,
  Layers,
  Loader2,
  Search,
  Wand2,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

const REASONING_TRACE = [
  { key: "parse",   label: "Parsing goal",             detail: "Extracting entities, verbs, objects." },
  { key: "world",   label: "Retrieving world state",   detail: "Loading grounded facts for candidate + job." },
  { key: "capmatch",label: "Matching capabilities",    detail: "Scanning the registry for callable actions." },
  { key: "score",   label: "Scoring & ordering steps", detail: "Composing a confident, policy-safe plan." },
  { key: "verify",  label: "Schema-validating plan",   detail: "Filtering invalid capability IDs at the edge." },
];

export default function PlannerView() {
  const [goal, setGoal] = useState(
    "Screen candidate cand_ai_staff_bang_00 for job job_ai_staff_bang",
  );
  const [context, setContext] = useState(
    '{"candidate_id":"cand_ai_staff_bang_00","job_id":"job_ai_staff_bang"}',
  );
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [traceIdx, setTraceIdx] = useState(-1);

  useEffect(() => {
    if (!loading) return undefined;
    setTraceIdx(0);
    let step = 0;
    const id = setInterval(() => {
      step += 1;
      if (step >= REASONING_TRACE.length) clearInterval(id);
      else setTraceIdx(step);
    }, 1100);
    return () => clearInterval(id);
  }, [loading]);

  const run = async () => {
    setLoading(true);
    setErr(null);
    try {
      const parsedContext = context.trim() ? JSON.parse(context) : {};
      const { data } = await api.post("/planner/plan", {
        goal,
        context: parsedContext,
      });
      setPlan(data);
    } catch (e) {
      setErr(String(e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.plannerRoot} className="p-6 space-y-4">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            HIRING PLANNER
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Proposes plans. Never executes.
          </h1>
          <div className="text-slate-500 text-sm">
            Claude Sonnet 4.5 grounds against world state and returns a
            deterministic, schema-validated plan. Invalid capability IDs are
            filtered by the runtime.
          </div>
        </div>

        <div className="border border-slate-800 bg-slate-900 rounded-md p-4 space-y-3">
          <div>
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
              GOAL
            </div>
            <input
              data-testid={EAROS.plannerGoalInput}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[13px] text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
              CONTEXT · JSON
            </div>
            <textarea
              data-testid={EAROS.plannerContextInput}
              rows={4}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            data-testid={EAROS.plannerRunBtn}
            onClick={run}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2 disabled:opacity-50"
          >
            <Wand2 className="w-3.5 h-3.5" strokeWidth={1.5} />
            {loading ? "PLANNING…" : "GENERATE PLAN"}
          </button>
          {err && <div className="text-rose-400 text-[12px]">{err}</div>}
        </div>

        {(loading || plan) && (
          <div
            data-testid="planner-reasoning-trace"
            className="border border-indigo-500/40 bg-indigo-500/[0.03] rounded-md p-4"
          >
            <div className="font-mono2 text-[10px] tracking-widest text-indigo-300 mb-3 flex items-center gap-2">
              <Search className="w-3 h-3" strokeWidth={1.5} />
              PLANNER REASONING TRACE
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-0 md:divide-x divide-slate-800/60">
              {REASONING_TRACE.map((r, i) => {
                const done = (!loading && !!plan) || i < traceIdx;
                const active = loading && i === traceIdx;
                return (
                  <div key={r.key} className="p-2">
                    <div className="flex items-center gap-1.5 mb-1">
                      {done ? (
                        <CheckCircle2
                          className="w-3.5 h-3.5 text-emerald-400"
                          strokeWidth={1.5}
                        />
                      ) : active ? (
                        <Loader2
                          className="w-3.5 h-3.5 text-indigo-300 animate-spin"
                          strokeWidth={1.5}
                        />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-slate-700" />
                      )}
                      <div
                        className={`font-mono2 text-[9px] tracking-widest ${
                          done ? "text-emerald-400" : active ? "text-indigo-300" : "text-slate-600"
                        }`}
                      >
                        {r.label.toUpperCase()}
                      </div>
                    </div>
                    <div
                      className={`text-[11px] ${
                        done || active ? "text-slate-300" : "text-slate-500"
                      }`}
                    >
                      {r.detail}
                    </div>
                  </div>
                );
              })}
            </div>
            {plan && (
              <div className="mt-3 pt-3 border-t border-slate-800 flex items-center gap-4 text-[12px]">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" strokeWidth={1.5} />
                  Dispatched · <span className="text-slate-100 font-mono2">{plan.steps.length}</span> steps
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Layers className="w-3.5 h-3.5 text-amber-400" strokeWidth={1.5} />
                  Capabilities · <span className="text-slate-100 font-mono2">
                    {new Set(plan.steps.map((s) => s.capability_id)).size}
                  </span> unique
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  Avg confidence · <span className="text-emerald-400 font-mono2">
                    {plan.steps.length
                      ? Math.round(
                          (plan.steps.reduce((s, x) => s + x.confidence, 0) /
                            plan.steps.length) *
                            100,
                        )
                      : 0}
                    %
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {plan && (
          <>
            <AIDecisionCard rec={plan.recommendation} />
            <div className="border border-slate-800 bg-slate-900 rounded-md">
              <div className="p-3 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
                PROPOSED STEPS · {plan.steps.length}
              </div>
              <div className="divide-y divide-slate-800/60">
                {plan.steps.map((s, i) => (
                  <div
                    key={s.step_id}
                    className="p-3 grid grid-cols-[36px_1fr_100px] gap-3 items-start text-[12px]"
                  >
                    <span className="font-mono2 text-indigo-400">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <div className="font-mono2 text-slate-100">{s.capability_id}</div>
                      <div className="font-mono2 text-slate-500 text-[11px] break-all">
                        {JSON.stringify(s.inputs)}
                      </div>
                      {s.description && (
                        <div className="text-slate-400 text-[12px] mt-1">
                          {s.description}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-mono2 text-emerald-400 text-[13px]">
                        {Math.round(s.confidence * 100)}%
                      </div>
                      <div className="font-mono2 text-[10px] text-slate-500">
                        {s.sensitivity}
                      </div>
                    </div>
                  </div>
                ))}
                {plan.steps.length === 0 && (
                  <div className="p-6 text-center text-slate-500 text-[12px]">
                    Planner returned zero steps.
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
