import React, { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ChevronRight,
  Cpu,
  FileText,
  HandMetal,
  Mail,
  MapPin,
  MessageSquare,
  Play,
  Send,
  Sparkles,
  UploadCloud,
  Users2,
  Wand2,
  X,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";
import AIDecisionCard from "@/components/ai/AIDecisionCard";

const fetcher = (url) => api.get(url).then((r) => r.data);

const STAGE_TINT = {
  sourced: "text-slate-400 bg-slate-500/10 border-slate-500/30",
  screening: "text-indigo-300 bg-indigo-500/10 border-indigo-500/30",
  phone_screen: "text-violet-300 bg-violet-500/10 border-violet-500/30",
  technical: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30",
  onsite: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  offer: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30",
  hired: "text-emerald-200 bg-emerald-500/20 border-emerald-500/50",
  rejected: "text-rose-300 bg-rose-500/10 border-rose-500/30",
  withdrawn: "text-slate-500 bg-slate-800 border-slate-700",
};

function JobPicker({ jobs, jobId, setJobId }) {
  return (
    <div
      data-testid={EAROS.jobPicker}
      className="w-72 shrink-0 border-r border-slate-800/80 bg-slate-950 overflow-y-auto"
    >
      <div className="p-3 border-b border-slate-800/80 sticky top-0 bg-slate-950">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
          OPEN REQUISITIONS
        </div>
        <div className="text-slate-100 text-sm">
          {jobs?.length ?? 0} active
        </div>
      </div>
      {jobs?.map((j) => (
        <button
          key={j.job_id}
          data-testid={EAROS.jobPickerItem(j.job_id)}
          onClick={() => setJobId(j.job_id)}
          className={`w-full text-left px-3 py-3 border-b border-slate-800/40 transition-colors ${
            jobId === j.job_id
              ? "bg-slate-900 border-l-2 border-l-indigo-500"
              : "hover:bg-slate-900/60 border-l-2 border-l-transparent"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="text-slate-100 text-[13px] font-medium leading-snug">
              {j.title}
            </div>
            <span
              className={`shrink-0 px-1.5 py-0.5 rounded-sm text-[10px] font-mono2 border ${
                j.priority === "P0"
                  ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
                  : j.priority === "P1"
                    ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
                    : "text-slate-400 bg-slate-500/10 border-slate-500/30"
              }`}
            >
              {j.priority}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-[11px] text-slate-500 font-mono2">
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3" strokeWidth={1.5} />
              {j.location}
            </span>
            <span>{j.level}</span>
          </div>
        </button>
      ))}
    </div>
  );
}

function CandidateList({ candidates, selected, setSelected }) {
  return (
    <div className="w-96 shrink-0 border-r border-slate-800/80 bg-slate-950 overflow-y-auto">
      <div className="p-3 border-b border-slate-800/80 sticky top-0 bg-slate-950">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
          CANDIDATES
        </div>
        <div className="text-slate-100 text-sm">
          {candidates?.length ?? 0} in pipeline
        </div>
      </div>
      {candidates?.map((c) => (
        <button
          key={c.candidate_id}
          data-testid={EAROS.candidateRow(c.candidate_id)}
          onClick={() => setSelected(c.candidate_id)}
          className={`w-full text-left px-3 py-3 border-b border-slate-800/40 transition-colors ${
            selected === c.candidate_id ? "bg-slate-900" : "hover:bg-slate-900/60"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-slate-100 text-[13px] font-medium truncate">
                {c.full_name}
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                {c.current_title} · {c.current_company}
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-600" strokeWidth={1.5} />
          </div>
          <div className="mt-2 flex items-center gap-2 text-[10px] font-mono2">
            <span
              className={`px-1.5 py-0.5 rounded-sm border ${
                STAGE_TINT[c.stage] || STAGE_TINT.sourced
              }`}
            >
              {c.stage}
            </span>
            <span className="text-slate-500">
              {c.years_experience.toFixed(1)}y · {c.currency}{" "}
              {(c.expected_salary / 1000).toFixed(0)}k
            </span>
          </div>
        </button>
      ))}
      {candidates?.length === 0 && (
        <div className="p-6 text-center text-slate-500 text-[12px]">
          No candidates for this req.
        </div>
      )}
    </div>
  );
}

function PlanPanel({ plan, onExecute, executing }) {
  if (!plan) return null;
  return (
    <div className="border border-slate-800 bg-slate-900 rounded-md">
      <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
        <div>
          <div className="font-mono2 text-[10px] tracking-widest text-indigo-400">
            PROPOSED EXECUTION PLAN
          </div>
          <div className="font-display text-base font-bold text-slate-100">
            {plan.recommendation?.title}
          </div>
        </div>
        <button
          data-testid={EAROS.executePlanBtn}
          onClick={() => onExecute(plan)}
          disabled={executing || plan.steps.length === 0}
          className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2 disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
          {executing ? "EXECUTING…" : "APPROVE & EXECUTE PLAN"}
        </button>
      </div>
      <div className="p-4">
        <div className="text-[12px] text-slate-400 mb-3">
          {plan.recommendation?.summary}
        </div>
        <div className="space-y-2">
          {plan.steps.map((s, i) => (
            <div
              key={s.step_id}
              data-testid={EAROS.planStepRow(s.step_id)}
              className="flex items-center gap-3 border border-slate-800 bg-slate-950 rounded-sm p-2.5 text-[12px]"
            >
              <span className="font-mono2 text-indigo-400 shrink-0 w-6">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <div className="font-mono2 text-slate-100 text-[12px]">
                  {s.capability_id}
                </div>
                <div className="text-slate-500 text-[11px] truncate">
                  {s.description || JSON.stringify(s.inputs)}
                </div>
              </div>
              <span className="font-mono2 text-[11px] text-emerald-400">
                {(s.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
          {plan.steps.length === 0 && (
            <div className="text-slate-500 text-[12px] flex items-center gap-2 p-2">
              <AlertCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
              Planner returned no steps — try a different goal or context.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ExecutionResult({ result }) {
  if (!result) return null;
  const statusColor =
    {
      succeeded: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
      awaiting_approval: "text-amber-400 border-amber-500/30 bg-amber-500/10",
      policy_blocked: "text-rose-400 border-rose-500/30 bg-rose-500/10",
      failed: "text-rose-400 border-rose-500/30 bg-rose-500/10",
    }[result.status] || "text-slate-400 border-slate-500/30 bg-slate-500/10";
  return (
    <div className="border border-slate-800 bg-slate-900 rounded-md">
      <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
        <div>
          <div className="font-mono2 text-[10px] tracking-widest text-emerald-400">
            EXECUTION RESULT
          </div>
          <div className="font-mono2 text-[11px] text-slate-500">
            {result.execution_id}
          </div>
        </div>
        <span
          className={`px-2 py-1 rounded-sm border font-mono2 text-[10px] tracking-widest ${statusColor}`}
        >
          {result.status.toUpperCase()}
        </span>
      </div>
      <div className="divide-y divide-slate-800/60">
        {result.step_results?.map((s, i) => (
          <div key={i} className="p-3 text-[12px]">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono2 text-slate-100">{s.capability_id}</span>
              <span
                className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${
                  s.ok
                    ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                    : "text-rose-400 border-rose-500/30 bg-rose-500/10"
                }`}
              >
                {s.ok ? "OK" : "FAIL"}
              </span>
              <span className="font-mono2 text-[10px] text-slate-500">
                policy · {s.policy_decision}
              </span>
            </div>
            {s.facts?.map((f, j) => (
              <div key={j} className="text-slate-400 font-mono2 text-[11px]">
                · {f}
              </div>
            ))}
            {s.error && (
              <div className="text-rose-400 font-mono2 text-[11px]">
                error · {s.error}
              </div>
            )}
            {s.approval_id && (
              <div className="text-amber-400 font-mono2 text-[11px]">
                approval requested · {s.approval_id}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RecruiterCopilot() {
  const [searchParams] = useSearchParams();
  const preselectJobId = searchParams.get("job");
  const [jobId, setJobId] = useState(preselectJobId);
  const [selectedCand, setSelectedCand] = useState(null);
  const [plan, setPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [executing, setExecuting] = useState(false);

  const { data: jobs } = useSWR("/world/jobs", fetcher);
  useEffect(() => {
    if (!jobs) return;
    if (preselectJobId && jobs.some((j) => j.job_id === preselectJobId)) {
      setJobId(preselectJobId);
    } else if (!jobId) {
      setJobId(jobs[0]?.job_id);
    }
  }, [jobs, jobId, preselectJobId]);

  const { data: candidates, mutate: mutateCandidates } = useSWR(
    jobId ? `/world/jobs/${jobId}/candidates` : null,
    fetcher,
  );
  useEffect(() => {
    setSelectedCand(null);
    setPlan(null);
    setExecResult(null);
  }, [jobId]);

  const { data: recs, mutate: mutateRecs } = useSWR(
    jobId ? `/intelligence/hiring/${jobId}?top_n=5` : null,
    fetcher,
  );

  const [toast, setToast] = useState(null);
  const showToast = (msg, tone = "emerald") => {
    setToast({ msg, tone });
    setTimeout(() => setToast(null), 4000);
  };

  const selectedCandDetails = useMemo(
    () => candidates?.find((c) => c.candidate_id === selectedCand),
    [candidates, selectedCand],
  );

  const executeRec = async (rec) => {
    setExecuting(true);
    try {
      const { data } = await api.post("/runtime/execute", {
        goal: rec.title,
        decision_id: rec.decision_id,
        steps: [
          {
            capability_id: rec.action,
            inputs: rec.inputs,
            confidence: rec.confidence.value,
          },
        ],
      });
      setExecResult(data);
      // Refresh candidate list to reflect stage change; leave recs stable so
      // the user sees the same card they just approved rather than a new set.
      await mutateCandidates();
      const status = data.status;
      if (status === "succeeded") {
        showToast(`Executed · ${rec.action} · World State updated`, "emerald");
      } else if (status === "awaiting_approval") {
        showToast("Held for human approval — see Governance", "amber");
      } else if (status === "policy_blocked") {
        showToast(`Blocked by policy: ${data.error || "denied"}`, "rose");
      } else {
        showToast(`Execution ${status}`, "rose");
      }
    } catch (e) {
      setExecResult({
        execution_id: "-",
        status: "failed",
        step_results: [{ capability_id: rec.action, ok: false, error: String(e) }],
      });
      showToast(`Failed: ${String(e).slice(0, 80)}`, "rose");
    } finally {
      setExecuting(false);
    }
  };

  const simulatePlan = async () => {
    if (!selectedCand) return;
    setPlanLoading(true);
    setPlan(null);
    try {
      const { data } = await api.post("/planner/plan", {
        goal: `Screen and advance ${selectedCandDetails?.full_name}`,
        context: { candidate_id: selectedCand, job_id: jobId },
      });
      setPlan(data);
    } finally {
      setPlanLoading(false);
    }
  };

  const executePlan = async (p) => {
    setExecuting(true);
    try {
      const { data } = await api.post("/runtime/execute", {
        goal: p.goal,
        decision_id: p.recommendation.decision_id,
        steps: p.steps.map((s) => ({
          capability_id: s.capability_id,
          inputs: s.inputs,
          confidence: s.confidence,
          sensitivity: s.sensitivity,
          description: s.description,
        })),
      });
      setExecResult(data);
    } finally {
      setExecuting(false);
    }
  };

  // -------- Task 4: autonomy mode, stage transitions, ops tools --------
  const [autonomyMode, setAutonomyMode] = useState("semi");
  const [openTool, setOpenTool] = useState(null);
  const [tick, setTick] = useState(0);

  const changeStage = async (newStage) => {
    if (!selectedCand) return;
    try {
      await api.post(`/world/candidates/${selectedCand}/stage`, {
        stage: newStage,
        reason: `manual transition · autonomy=${autonomyMode}`,
      });
      await mutateCandidates();
      setTick((t) => t + 1);
      showToast(`Moved to ${newStage} · World State + audit updated`, "emerald");
    } catch (e) {
      showToast(`Stage change failed: ${String(e).slice(0, 80)}`, "rose");
    }
  };

  return (
    <AppLayout>
      {toast && (
        <div className={`fixed top-16 right-4 z-50 px-4 py-2.5 rounded-sm border backdrop-blur-sm font-mono2 text-[12px] shadow-lg ${
          toast.tone === "emerald" ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-200" :
          toast.tone === "amber" ? "bg-amber-500/20 border-amber-500/40 text-amber-200" :
          "bg-rose-500/20 border-rose-500/40 text-rose-200"
        }`}>
          {toast.msg}
        </div>
      )}
      <div
        data-testid={EAROS.recruiterRoot}
        className="flex h-[calc(100vh-3.5rem)]"
      >
        <JobPicker jobs={jobs} jobId={jobId} setJobId={setJobId} />
        <CandidateList
          candidates={candidates}
          selected={selectedCand}
          setSelected={setSelectedCand}
        />

        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-950">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-mono2 text-[10px] tracking-widest text-indigo-400">
                RECRUITER COPILOT
              </div>
              <h1 className="font-display text-2xl font-black tracking-tight">
                {selectedCandDetails
                  ? selectedCandDetails.full_name
                  : "AI-ranked shortlist"}
              </h1>
              <div className="text-slate-500 text-sm">
                {selectedCandDetails
                  ? `${selectedCandDetails.current_title} · ${selectedCandDetails.current_company} · ${selectedCandDetails.location}`
                  : `Top candidates for ${jobs?.find((j) => j.job_id === jobId)?.title || ""}`}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <AutonomyToggle mode={autonomyMode} setMode={setAutonomyMode} />
              {selectedCand && (
                <button
                  data-testid={EAROS.simulatePlanBtn}
                  onClick={simulatePlan}
                  disabled={planLoading}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2 disabled:opacity-50"
                >
                  <Wand2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                  {planLoading ? "PLANNING…" : "SIMULATE PLAN"}
                </button>
              )}
            </div>
          </div>

          <PipelineIntel candidates={candidates} autonomyMode={autonomyMode} />

          <OpsToolbar onLaunch={(t) => setOpenTool(t)} />

          {selectedCandDetails && (
            <div
              data-testid="candidate-detail-card"
              className="border border-slate-800 bg-slate-900 rounded-md p-4 flex flex-wrap items-center gap-6"
            >
              <div className="min-w-0">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
                  CANDIDATE
                </div>
                <div className="font-display text-lg font-bold text-slate-100">
                  {selectedCandDetails.full_name}
                </div>
                <div className="text-[12px] text-slate-500">
                  {selectedCandDetails.years_experience.toFixed(1)}y ·{" "}
                  {selectedCandDetails.location} ·{" "}
                  <span className="font-mono2 text-emerald-400">
                    fit {Math.round((selectedCandDetails.fit_score || 0) * 100)}%
                  </span>
                </div>
              </div>
              <StageTransition
                key={`${selectedCand}-${tick}`}
                candidate={selectedCandDetails}
                onChange={changeStage}
              />
              <div className="flex flex-wrap gap-1 min-w-0">
                {(selectedCandDetails.skills || [])
                  .slice(0, 6)
                  .map((s) => (
                    <span
                      key={s}
                      className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border border-slate-700 text-slate-400"
                    >
                      {s}
                    </span>
                  ))}
              </div>
            </div>
          )}

          {plan && (
            <PlanPanel plan={plan} onExecute={executePlan} executing={executing} />
          )}
          {execResult && <ExecutionResult result={execResult} />}

          <div className="space-y-4">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              HIRING PLANNER · TOP RECOMMENDATIONS
            </div>
            {recs?.recommendations
              ?.filter(
                (r) => !selectedCand || r.inputs?.candidate_id === selectedCand,
              )
              .map((r) => (
                <AIDecisionCard
                  key={r.decision_id}
                  rec={r}
                  onExecute={executeRec}
                  executing={executing}
                />
              ))}
            {selectedCand &&
              !recs?.recommendations?.find(
                (r) => r.inputs?.candidate_id === selectedCand,
              ) && (
                <div className="p-4 border border-slate-800 bg-slate-900 rounded-md text-slate-400 text-[13px]">
                  This candidate isn&apos;t in the top-5 planner ranking — try
                  “Simulate Plan” above, or select another candidate.
                </div>
              )}
          </div>
        </div>
      </div>

      {openTool && (
        <OpsModal
          tool={openTool}
          candidates={candidates}
          onClose={() => setOpenTool(null)}
          onSend={(t) => showToast(`${t.label} executed`, "emerald")}
        />
      )}
    </AppLayout>
  );
}


/* ============================================================
   TASK 4 — Recruiter operational surface
   ============================================================ */

const AUTONOMY_MODES = [
  { id: "manual",   label: "Manual",    icon: HandMetal,
    desc: "AI recommends. Recruiter clicks every action." },
  { id: "semi",     label: "Semi-auto", icon: Cpu,
    desc: "AI acts on low-risk steps. Human approves offers, comp, comms." },
  { id: "full",     label: "Full-auto", icon: Zap,
    desc: "AI runs the full lifecycle within policy. Human audits after." },
];

function AutonomyToggle({ mode, setMode }) {
  return (
    <div
      data-testid="autonomy-toggle"
      className="inline-flex items-center gap-0 border border-slate-800 rounded-sm bg-slate-950/60 p-0.5"
    >
      {AUTONOMY_MODES.map((m) => {
        const Icon = m.icon;
        const active = mode === m.id;
        return (
          <button
            key={m.id}
            data-testid={`autonomy-mode-${m.id}`}
            title={m.desc}
            onClick={() => setMode(m.id)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm font-mono2 text-[11px] transition ${
              active
                ? "bg-indigo-500/25 text-indigo-200 border border-indigo-500/40"
                : "text-slate-500 hover:text-slate-300 border border-transparent"
            }`}
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
            {m.label.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}

const STAGE_ORDER_FE = [
  "sourced", "screening", "phone_screen", "technical",
  "onsite", "offer", "hired", "rejected", "withdrawn",
];

function StageTransition({ candidate, onChange, disabled }) {
  const current = candidate?.stage;
  const [busy, setBusy] = useState(false);
  const [pendingStage, setPendingStage] = useState("");

  const handleChange = async (stage) => {
    if (!stage || stage === current || busy) return;
    setBusy(true);
    setPendingStage(stage);
    try {
      await onChange(stage);
    } finally {
      setBusy(false);
      setPendingStage("");
    }
  };

  return (
    <div
      data-testid="stage-transition"
      className="flex items-center gap-2"
    >
      <span className="font-mono2 text-[10px] text-slate-500 uppercase tracking-widest">
        Stage
      </span>
      <select
        data-testid="stage-transition-select"
        disabled={disabled || busy}
        value={pendingStage || current || ""}
        onChange={(e) => handleChange(e.target.value)}
        className="px-2 py-1.5 bg-slate-950 border border-slate-700 rounded-sm text-slate-100 text-[12px] font-mono2 focus:outline-none focus:border-indigo-500/60 disabled:opacity-40"
      >
        {STAGE_ORDER_FE.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      {busy && (
        <span className="font-mono2 text-[10px] text-indigo-300">saving…</span>
      )}
    </div>
  );
}

function PipelineIntel({ candidates, autonomyMode }) {
  const counts = useMemo(() => {
    const c = {};
    (candidates || []).forEach((cand) => {
      c[cand.stage] = (c[cand.stage] || 0) + 1;
    });
    return c;
  }, [candidates]);

  const active = (candidates || []).filter(
    (c) => !["hired", "rejected", "withdrawn"].includes(c.stage),
  );
  const withFit = active.filter((c) => (c.fit_score || 0) > 0);
  const avgFit = withFit.length
    ? withFit.reduce((s, c) => s + (c.fit_score || 0), 0) / withFit.length
    : null;
  const riskCount = (candidates || []).filter(
    (c) => (c.risk_flags || []).length > 0,
  ).length;

  return (
    <div
      data-testid="pipeline-intel"
      className="grid grid-cols-2 md:grid-cols-5 gap-2 border border-slate-800 bg-slate-900/40 rounded-md p-3"
    >
      <IntelCell label="Active" value={active.length} tone="cyan" />
      <IntelCell
        label="Avg fit"
        value={avgFit != null ? `${Math.round(avgFit * 100)}%` : "—"}
        tone="emerald"
      />
      <IntelCell
        label="Risk flags"
        value={riskCount}
        tone={riskCount > 0 ? "rose" : "slate"}
      />
      <IntelCell label="Offers" value={counts.offer || 0} tone="amber" />
      <IntelCell
        label="Autonomy"
        value={autonomyMode.toUpperCase()}
        tone="indigo"
        mono
      />
    </div>
  );
}

function IntelCell({ label, value, tone = "slate", mono }) {
  const toneClass = {
    cyan:    "text-cyan-300",
    emerald: "text-emerald-300",
    rose:    "text-rose-300",
    amber:   "text-amber-300",
    indigo:  "text-indigo-300",
    slate:   "text-slate-300",
  }[tone];
  return (
    <div className="min-w-0">
      <div className="font-mono2 text-[9px] tracking-widest text-slate-500 uppercase">
        {label}
      </div>
      <div
        className={`${mono ? "font-mono2 text-[13px]" : "font-display font-black text-xl"} truncate ${toneClass}`}
      >
        {value}
      </div>
    </div>
  );
}

const OPS_TOOLS = [
  {
    id: "email",   label: "Email campaign",   icon: Mail,
    subject: "You caught our team's attention",
    body: "Hi {{first_name}},\n\nYour work on {{signal}} lines up with what we're building. 15-min chat this week?\n\n— Priya, LevelShift",
  },
  {
    id: "sms",     label: "SMS campaign",     icon: MessageSquare,
    subject: "",
    body: "Hi {{first_name}}, Priya @ LevelShift — quick chat about a {{role}} role? Reply YES for details.",
  },
  {
    id: "screen",  label: "Screening blast",  icon: Send,
    subject: "5-min AI screening for {{role}}",
    body: "You'll get 3 questions — technical + culture. Answers reviewed by our AI screener within 4 hours.",
  },
  {
    id: "harvest", label: "Resume harvester", icon: UploadCloud,
    subject: "",
    body: "Drag-and-drop resumes to auto-parse, extract structured signal, and dedupe against the ATS.",
  },
];

function OpsToolbar({ onLaunch }) {
  return (
    <div
      data-testid="ops-toolbar"
      className="grid grid-cols-2 md:grid-cols-4 gap-2"
    >
      {OPS_TOOLS.map((t) => {
        const Icon = t.icon;
        return (
          <button
            key={t.id}
            data-testid={`ops-tool-${t.id}`}
            onClick={() => onLaunch(t)}
            className="flex items-center gap-2 p-3 border border-slate-800 hover:border-indigo-500/60 bg-slate-900/60 hover:bg-slate-900 rounded-sm text-left transition"
          >
            <Icon className="w-4 h-4 text-indigo-300 shrink-0" strokeWidth={1.5} />
            <div className="min-w-0">
              <div className="text-slate-100 text-[12px] font-medium truncate">
                {t.label}
              </div>
              <div className="text-slate-500 text-[10px] font-mono2 truncate">
                launch →
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function OpsModal({ tool, candidates, onClose, onSend }) {
  const [subject, setSubject] = useState(tool.subject);
  const [body, setBody] = useState(tool.body);
  const [selected, setSelected] = useState(
    (candidates || []).slice(0, 3).map((c) => c.candidate_id),
  );
  const [sending, setSending] = useState(false);
  const [sentCount, setSentCount] = useState(null);

  const toggle = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const handleSend = async () => {
    setSending(true);
    // Simulate a paced send — each candidate ticks ~180ms
    for (let i = 0; i < selected.length; i++) {
      // Yield to render cycle
      await new Promise((r) => setTimeout(r, 180));
    }
    setSentCount(selected.length);
    setSending(false);
    if (onSend) onSend(tool, selected);
  };

  const Icon = tool.icon;

  return (
    <div
      data-testid="ops-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col bg-slate-950 border border-slate-800 rounded-md shadow-2xl">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Icon className="w-4 h-4 text-indigo-300" strokeWidth={1.5} />
            <div>
              <div className="font-mono2 text-[10px] tracking-widest text-indigo-300">
                RECRUITER OPS
              </div>
              <div className="font-display text-base font-bold text-slate-100">
                {tool.label}
              </div>
            </div>
          </div>
          <button
            data-testid="ops-modal-close"
            onClick={onClose}
            className="p-1.5 rounded-sm hover:bg-slate-800 text-slate-400"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {sentCount === null ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {tool.id !== "harvest" && (
              <>
                {tool.subject !== undefined && tool.id !== "sms" && (
                  <div>
                    <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                      SUBJECT
                    </div>
                    <input
                      data-testid="ops-modal-subject"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-sm text-slate-100 text-[13px] focus:outline-none focus:border-indigo-500/60"
                    />
                  </div>
                )}
                <div>
                  <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                    MESSAGE · {`{{first_name}}`}, {`{{role}}`}, {`{{signal}}`} auto-filled
                  </div>
                  <textarea
                    data-testid="ops-modal-body"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={tool.id === "sms" ? 3 : 7}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-sm text-slate-100 text-[13px] font-mono2 focus:outline-none focus:border-indigo-500/60"
                  />
                </div>
                <div>
                  <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
                    RECIPIENTS · {selected.length} selected
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1 max-h-56 overflow-y-auto">
                    {(candidates || []).map((c) => (
                      <label
                        key={c.candidate_id}
                        data-testid={`ops-recipient-${c.candidate_id}`}
                        className="flex items-center gap-2 p-2 border border-slate-800 bg-slate-900/50 rounded-sm text-[12px] cursor-pointer hover:border-indigo-500/40"
                      >
                        <input
                          type="checkbox"
                          checked={selected.includes(c.candidate_id)}
                          onChange={() => toggle(c.candidate_id)}
                          className="accent-indigo-500"
                        />
                        <span className="text-slate-100 truncate flex-1">
                          {c.full_name}
                        </span>
                        <span className="font-mono2 text-[10px] text-slate-500">
                          {c.stage}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}
            {tool.id === "harvest" && (
              <div>
                <div className="p-6 border border-dashed border-slate-700 rounded-sm text-center">
                  <UploadCloud
                    className="w-8 h-8 mx-auto text-slate-600 mb-2"
                    strokeWidth={1.25}
                  />
                  <div className="text-slate-300 text-[13px]">
                    Drop .pdf / .docx resumes here
                  </div>
                  <div className="text-slate-500 text-[11px] mt-1">
                    AI will parse, extract structured signal, dedupe against ATS,
                    and enqueue matches for this req.
                  </div>
                </div>
                <div className="mt-3 font-mono2 text-[10px] text-slate-500 tracking-widest">
                  ATS DEDUPE PREVIEW — {candidates?.length ?? 0} existing candidates
                  matched on email/phone/LinkedIn URL.
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-8 text-center">
            <div className="mx-auto w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mb-4">
              <Send className="w-6 h-6 text-emerald-300" strokeWidth={1.5} />
            </div>
            <div className="font-display text-xl font-black text-slate-100">
              {tool.id === "harvest"
                ? "Resumes queued"
                : `Sent to ${sentCount} candidate${sentCount === 1 ? "" : "s"}`}
            </div>
            <div className="text-slate-400 text-[12.5px] mt-2 max-w-md mx-auto">
              {tool.id === "harvest"
                ? "Parsing in the background — check the pipeline in ~2 minutes."
                : `Personalization applied per candidate. Delivery tracked in Governance.`}
            </div>
          </div>
        )}

        <div className="px-5 py-3 border-t border-slate-800 flex items-center justify-between">
          <div className="font-mono2 text-[10px] text-slate-500">
            {sentCount === null
              ? tool.id === "harvest"
                ? "READY TO PARSE"
                : `${selected.length} RECIPIENT${selected.length === 1 ? "" : "S"} · POLICY-CHECKED`
              : "COMPLETE"}
          </div>
          {sentCount === null ? (
            <button
              data-testid="ops-modal-send"
              onClick={handleSend}
              disabled={sending || (tool.id !== "harvest" && selected.length === 0)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" strokeWidth={1.5} />
              {sending
                ? "SENDING…"
                : tool.id === "harvest"
                  ? "START PARSE"
                  : "SEND CAMPAIGN"}
            </button>
          ) : (
            <button
              data-testid="ops-modal-done"
              onClick={onClose}
              className="px-4 py-2 rounded-sm border border-slate-700 hover:border-indigo-500/60 text-slate-300 text-[12px] font-mono2"
            >
              DONE
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

