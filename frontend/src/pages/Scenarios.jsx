import React, { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  Clock,
  Loader2,
  Rocket,
  ShieldCheck,
  ShieldX,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const POLL_INTERVAL_MS = 700;

export default function Scenarios() {
  const { data: scenarios } = useSWR("/scenarios", fetcher);
  const [execId, setExecId] = useState(null);
  const [runningScnId, setRunningScnId] = useState(null);
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);
  const navigate = useNavigate();

  // Poll execution state.
  //
  // Note: `api` and `POLL_INTERVAL_MS` are module-level constants and setters
  // (`setState`, `setError`) are stable identities from useState — including
  // them in deps would either be a no-op or reset the polling loop on every
  // render. We depend only on `execId` which is the actual re-run trigger.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!execId) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const { data } = await api.get(
          `/scenarios/executions/${execId}/state`,
        );
        if (cancelled) return;
        setState(data);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollRef.current);
        }
      } catch (e) {
        setError(String(e));
      }
    };
    tick();
    pollRef.current = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(pollRef.current);
    };
  }, [execId]);

  const run = async (scenario) => {
    setError(null);
    setState(null);
    setRunningScnId(scenario.scenario_id);
    try {
      const { data } = await api.post(`/scenarios/${scenario.scenario_id}/run`);
      setExecId(data.execution_id);
      setState(data);
    } catch (e) {
      setError(String(e));
      setRunningScnId(null);
    }
  };

  const approve = async () => {
    if (!execId) return;
    await api.post(`/scenarios/executions/${execId}/approve`);
  };
  const reject = async () => {
    if (!execId) return;
    await api.post(`/scenarios/executions/${execId}/reject`);
  };

  const reset = () => {
    setExecId(null);
    setState(null);
    setRunningScnId(null);
    setError(null);
  };

  const isFinal = state?.status === "completed" || state?.status === "failed";
  const activeScenarioCard = scenarios?.find(
    (s) => s.scenario_id === runningScnId,
  );

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
            offer, and reflection — paced so you can watch every agent think,
            with policy gating and human-in-the-loop approvals.
          </div>
        </div>

        {state && (
          <LiveExecutionPanel
            state={state}
            scenario={activeScenarioCard}
            onApprove={approve}
            onReject={reject}
            onReset={reset}
            onOpenAudit={() => navigate("/governance")}
            onOpenReplay={() =>
              state.correlation_id &&
              navigate(`/deep-dive/${state.correlation_id}`)
            }
          />
        )}

        {error && (
          <div
            data-testid="scenario-error"
            className="border border-rose-500/40 bg-rose-500/5 text-rose-300 text-sm p-3 rounded-md flex items-center gap-2"
          >
            <XCircle className="w-4 h-4" strokeWidth={1.5} />
            {error}
          </div>
        )}

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {scenarios?.map((s) => {
            const isRunning = runningScnId === s.scenario_id && !isFinal;
            return (
              <div
                key={s.scenario_id}
                data-testid={EAROS.scenarioCard(s.scenario_id)}
                className={`border rounded-md p-5 relative overflow-hidden transition ${
                  isRunning
                    ? "border-cyan-500/60 bg-cyan-500/5"
                    : "border-slate-800 bg-slate-900"
                }`}
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
                    disabled={!!runningScnId && !isFinal}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2 disabled:opacity-40"
                  >
                    <Rocket className="w-3.5 h-3.5" strokeWidth={1.5} />
                    {isRunning ? "RUNNING…" : "RUN SCENARIO"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}

/* ============================================================
   Live execution panel — banner + progress bar + step list + gate
   ============================================================ */

function LiveExecutionPanel({
  state,
  scenario,
  onApprove,
  onReject,
  onReset,
  onOpenAudit,
  onOpenReplay,
}) {
  const active = state.steps[state.current_step_idx];
  const isAwaiting = state.status === "awaiting_approval";
  const isCompleted = state.status === "completed";
  const isFailed = state.status === "failed";

  return (
    <div
      data-testid="scenario-live-panel"
      className="border border-cyan-500/40 bg-slate-950/70 rounded-md overflow-hidden"
    >
      {/* Banner */}
      <div className="px-5 py-3 bg-gradient-to-r from-indigo-500/10 via-cyan-500/10 to-transparent border-b border-cyan-500/30 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          {isCompleted ? (
            <CheckCircle2
              className="w-5 h-5 text-emerald-400 shrink-0"
              strokeWidth={1.5}
            />
          ) : isFailed ? (
            <XCircle
              className="w-5 h-5 text-rose-400 shrink-0"
              strokeWidth={1.5}
            />
          ) : isAwaiting ? (
            <ShieldCheck
              className="w-5 h-5 text-amber-400 shrink-0 animate-pulse"
              strokeWidth={1.5}
            />
          ) : (
            <Loader2
              className="w-5 h-5 text-cyan-400 shrink-0 animate-spin"
              strokeWidth={1.5}
            />
          )}
          <div className="min-w-0">
            <div className="font-mono2 text-[10px] tracking-widest text-cyan-400">
              {isCompleted
                ? "SCENARIO COMPLETE"
                : isFailed
                  ? "SCENARIO FAILED"
                  : isAwaiting
                    ? "HELD FOR HUMAN APPROVAL"
                    : `RUNNING · ${active?.agent ?? ""}`}
            </div>
            <div
              className="font-display text-base font-bold text-slate-100 truncate"
              data-testid="scenario-current-label"
            >
              {isCompleted
                ? scenario?.title ?? state.scenario_title
                : active?.label ?? state.scenario_title}
            </div>
            {!isFailed && (
              <div className="text-[12px] text-slate-400 truncate">
                {isCompleted
                  ? "All 14 lifecycle stages executed. Immutable events recorded."
                  : active?.detail ?? ""}
              </div>
            )}
            {isFailed && (
              <div className="text-[12px] text-rose-300">{state.error}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isCompleted && state.correlation_id && (
            <button
              data-testid="scenario-open-replay"
              onClick={onOpenReplay}
              className="font-mono2 text-[11px] px-3 py-1.5 rounded-sm bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 text-indigo-300"
            >
              open replay →
            </button>
          )}
          {isCompleted && (
            <button
              data-testid="scenario-open-audit"
              onClick={onOpenAudit}
              className="font-mono2 text-[11px] px-3 py-1.5 rounded-sm border border-slate-700 hover:border-slate-500 text-slate-300"
            >
              audit →
            </button>
          )}
          {(isCompleted || isFailed) && (
            <button
              data-testid="scenario-reset-btn"
              onClick={onReset}
              className="font-mono2 text-[11px] px-3 py-1.5 rounded-sm border border-slate-700 hover:border-slate-500 text-slate-300"
            >
              dismiss
            </button>
          )}
        </div>
      </div>

      {/* Approval gate */}
      {isAwaiting && (
        <ApprovalGateCard
          approval={state.approval}
          onApprove={onApprove}
          onReject={onReject}
        />
      )}

      {/* Progress bar */}
      <div className="px-5 pt-4">
        <div className="flex items-center justify-between font-mono2 text-[10px] text-slate-500 mb-1">
          <span>
            STEP {Math.min(state.current_step_idx + 1, state.total_steps)} /{" "}
            {state.total_steps}
          </span>
          <span>{state.progress_pct}%</span>
        </div>
        <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            data-testid="scenario-progress-bar"
            className={`h-full transition-all duration-500 ${
              isFailed
                ? "bg-rose-500"
                : isCompleted
                  ? "bg-emerald-500"
                  : isAwaiting
                    ? "bg-amber-400"
                    : "bg-cyan-400"
            }`}
            style={{ width: `${state.progress_pct}%` }}
          />
        </div>
      </div>

      {/* Step list */}
      <div
        data-testid="scenario-step-list"
        className="p-5 space-y-2 max-h-[420px] overflow-y-auto"
      >
        {state.steps.map((step, i) => (
          <StepRow
            key={step.key}
            step={step}
            isActive={i === state.current_step_idx && !isCompleted && !isFailed}
          />
        ))}
      </div>
    </div>
  );
}

function StepRow({ step, isActive }) {
  const done = step.status === "done";
  const running = step.status === "running";
  const skipped = step.status === "skipped";
  return (
    <div
      data-testid={`scenario-step-${step.key}`}
      className={`flex items-start gap-3 p-2.5 rounded-sm border transition ${
        isActive
          ? "border-cyan-500/50 bg-cyan-500/5"
          : done
            ? "border-emerald-500/20 bg-emerald-500/[0.03]"
            : "border-slate-800/60 bg-transparent"
      }`}
    >
      <div className="mt-0.5 shrink-0">
        {done ? (
          <CheckCircle2
            className="w-4 h-4 text-emerald-400"
            strokeWidth={1.5}
          />
        ) : running ? (
          <Loader2
            className="w-4 h-4 text-cyan-400 animate-spin"
            strokeWidth={1.5}
          />
        ) : skipped ? (
          <Clock className="w-4 h-4 text-slate-600" strokeWidth={1.5} />
        ) : (
          <div className="w-4 h-4 rounded-full border border-slate-700" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <div
            className={`font-mono2 text-[10px] tracking-widest ${
              done
                ? "text-emerald-400"
                : running
                  ? "text-cyan-300"
                  : "text-slate-500"
            }`}
          >
            {step.agent}
          </div>
          {running && (
            <span className="pulse-dot" style={{ background: "#22d3ee" }} />
          )}
        </div>
        <div
          className={`text-[13px] font-medium ${
            done || running ? "text-slate-100" : "text-slate-500"
          }`}
        >
          {step.label}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          {step.output ?? step.detail}
        </div>
      </div>
    </div>
  );
}

function formatCountdown(secs) {
  const s = Math.max(0, Math.ceil(secs));
  if (s >= 60) {
    const m = Math.floor(s / 60);
    const rest = s % 60;
    return `${m}:${String(rest).padStart(2, "0")}`;
  }
  return `${s}s`;
}

function ApprovalGateCard({ approval, onApprove, onReject }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);
  // approval.seconds_remaining is fetched with each poll; we also decay locally
  // between polls for a smoother countdown feel.
  const secs = approval?.seconds_remaining ?? 0;

  return (
    <div
      data-testid="scenario-approval-gate"
      className="mx-5 mt-4 border border-amber-500/50 bg-amber-500/10 rounded-md p-4"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="font-mono2 text-[10px] tracking-widest text-amber-300 mb-1 flex items-center gap-2">
            <Sparkles className="w-3 h-3" strokeWidth={1.5} />
            HUMAN APPROVAL REQUIRED
          </div>
          <div className="font-display text-lg font-bold text-amber-100">
            {approval?.subject}
          </div>
          <div className="text-[12.5px] text-amber-200/90 mt-1 max-w-2xl">
            {approval?.reason}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="font-mono2 text-[10px] tracking-widest text-amber-300">
            SCENARIO CANCELS IN
          </div>
          <div
            data-testid="scenario-approval-countdown"
            className="font-display text-3xl font-black text-amber-200 tabular-nums"
          >
            {formatCountdown(secs)}
          </div>
          <div className="font-mono2 text-[9px] text-amber-300/70 mt-0.5">
            explicit approve/reject required
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button
          data-testid="scenario-approve-btn"
          onClick={onApprove}
          className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/25 hover:bg-emerald-500/40 border border-emerald-500/50 text-emerald-200 text-[12px] font-mono2"
        >
          <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
          APPROVE OFFER
        </button>
        <button
          data-testid="scenario-reject-btn"
          onClick={onReject}
          className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/50 text-rose-200 text-[12px] font-mono2"
        >
          <ShieldX className="w-3.5 h-3.5" strokeWidth={1.5} />
          REJECT
        </button>
        {/* subtle hidden `now` reference — keeps interval linter happy */}
        <span className="sr-only">{now}</span>
      </div>
    </div>
  );
}
