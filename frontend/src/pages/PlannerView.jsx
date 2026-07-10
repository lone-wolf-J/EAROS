import React, { useState } from "react";
import { Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

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
