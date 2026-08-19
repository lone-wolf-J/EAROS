import React, { useMemo, useState } from "react";
import useSWR from "swr";
import {
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileOutput,
  FileText,
  ListChecks,
  Loader2,
  Mail,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";

const fetcher = (url) => api.get(url).then((response) => response.data);

export const WORKFLOW_DEFINITIONS = [
  {
    key: "source",
    label: "Source consented prospects",
    description: "Identify in-tenant prospects with active recruiting consent; the shortlist never sends contact or changes a candidate.",
    icon: Search,
    entity: "requisition",
    goal: "Source consented prospects for this requisition",
    capability: "cap.source_requisition_prospects",
    tone: "text-emerald-200 border-emerald-500/30 bg-emerald-500/10",
  },
  {
    key: "match",
    label: "Match prospects",
    description: "Rank consented, in-tenant prospects against a requisition's recorded skill requirements.",
    icon: UsersRound,
    entity: "requisition",
    goal: "Match prospects for this requisition",
    capability: "cap.match_requisition",
    tone: "text-teal-200 border-teal-500/30 bg-teal-500/10",
  },
  {
    key: "score",
    label: "Score application",
    description: "Create an explainable skill-fit score and gap summary against the selected hiring plan.",
    icon: ClipboardCheck,
    entity: "application",
    goal: "Score this application",
    capability: "cap.score_application",
    tone: "text-sky-200 border-sky-500/30 bg-sky-500/10",
  },
  {
    key: "resume-analysis",
    label: "Analyze parsed resume",
    description: "Review stored parsed-resume evidence, strengths, and data gaps without re-parsing a file or changing a record.",
    icon: FileText,
    entity: "candidate",
    goal: "Analyze this candidate's parsed resume",
    capability: "cap.analyze_resume",
    tone: "text-cyan-200 border-cyan-500/30 bg-cyan-500/10",
  },
  {
    key: "outreach-draft",
    label: "Draft consented outreach",
    description: "Prepare a recruiter-reviewed email draft only when active recruiting consent is recorded; EAROS never sends it.",
    icon: Mail,
    entity: "candidate",
    goal: "Draft outreach for this candidate",
    capability: "cap.draft_outreach",
    tone: "text-fuchsia-200 border-fuchsia-500/30 bg-fuchsia-500/10",
  },
  {
    key: "interview",
    label: "Prepare interview",
    description: "Draft a structured evidence interview brief from current application and scorecard facts.",
    icon: ListChecks,
    entity: "interview",
    goal: "Create interview prep for this interview",
    capability: "cap.prepare_interview",
    tone: "text-violet-200 border-violet-500/30 bg-violet-500/10",
  },
  {
    key: "publication",
    label: "Prepare distribution",
    description: "Build a review packet for target boards; this workflow cannot publish to any external service.",
    icon: FileOutput,
    entity: "requisition",
    goal: "Prepare job publication packet for this requisition",
    capability: "cap.prepare_job_publication",
    tone: "text-amber-200 border-amber-500/30 bg-amber-500/10",
  },
  {
    key: "triage",
    label: "Triage workflow",
    description: "Surface missing scoring and scheduling work as recommendations without moving any candidate stage.",
    icon: BrainCircuit,
    entity: "requisition",
    goal: "Triage this requisition workflow",
    capability: "cap.triage_requisition",
    tone: "text-rose-200 border-rose-500/30 bg-rose-500/10",
  },
];

export const AUTONOMY_GUARDRAILS = [
  "source_shortlists_require_active_recruiting_consent",
  "resume_analysis_uses_existing_parsed_profiles_only",
  "outreach_is_draft_only_and_never_provider_delivered",
  "plans_remain_policy_gated_and_auditable",
];

function Selector({ label, value, onChange, options, emptyLabel }) {
  return (
    <label className="block space-y-1.5">
      <span className="font-mono2 text-[10px] tracking-widest text-slate-500">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded-sm border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-teal-400">
        <option value="">{emptyLabel}</option>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function Stat({ label, value }) {
  return <div className="rounded-sm border border-slate-800 bg-slate-950/50 px-3 py-2"><div className="font-mono2 text-[10px] tracking-widest text-slate-600">{label}</div><div className="mt-1 text-xl font-bold text-slate-100">{value}</div></div>;
}

export default function ATSAutonomy() {
  const [workflowKey, setWorkflowKey] = useState("match");
  const [requisitionId, setRequisitionId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [interviewId, setInterviewId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [plan, setPlan] = useState(null);
  const [execution, setExecution] = useState(null);
  const [error, setError] = useState("");
  const [planning, setPlanning] = useState(false);
  const [executing, setExecuting] = useState(false);
  const { data: requisitions = [] } = useSWR("/ats/requisitions", fetcher);
  const { data: candidates = [] } = useSWR("/ats/candidates", fetcher);
  const { data: applications = [] } = useSWR("/ats/applications", fetcher);
  const { data: interviews = [] } = useSWR("/ats/interviews", fetcher);
  const { data: distributionAdapters = [] } = useSWR("/ats/job-distribution/adapters", fetcher);
  const { data: approvals = [], mutate: mutateApprovals } = useSWR("/governance/approvals?status=pending", fetcher, { refreshInterval: 10000 });

  const workflow = WORKFLOW_DEFINITIONS.find((item) => item.key === workflowKey) || WORKFLOW_DEFINITIONS[0];
  const context = useMemo(() => {
    if (workflow.entity === "application") return applicationId ? { application_id: applicationId } : {};
    if (workflow.entity === "interview") return interviewId ? { interview_id: interviewId } : {};
    if (workflow.entity === "candidate") return candidateId ? { candidate_id: candidateId } : {};
    return requisitionId ? { requisition_id: requisitionId } : {};
  }, [workflow.entity, requisitionId, applicationId, interviewId, candidateId]);
  const isReady = Object.keys(context).length === 1;

  const planWorkflow = async () => {
    if (!isReady) return;
    setPlanning(true); setError(""); setPlan(null); setExecution(null);
    try {
      const response = await api.post("/planner/plan", { goal: workflow.goal, context });
      setPlan(response.data);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "EAROS could not prepare a governed plan.");
    } finally { setPlanning(false); }
  };

  const requestExecution = async () => {
    if (!plan?.steps?.length) return;
    setExecuting(true); setError("");
    try {
      const response = await api.post("/runtime/execute", { goal: plan.goal, steps: plan.steps });
      setExecution(response.data);
      await mutateApprovals();
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "EAROS could not submit the plan to the governed runtime.");
    } finally { setExecuting(false); }
  };

  const requisitionOptions = requisitions.map((item) => ({ value: item.requisition_id, label: `${item.title} · ${item.approval_status}` }));
  const candidateOptions = candidates.map((item) => ({ value: item.candidate_id, label: `${item.full_name} · ${item.current_title || "Candidate"}` }));
  const applicationOptions = applications.map((item) => ({ value: item.application_id, label: `${item.application_id} · ${item.current_stage_name}` }));
  const interviewOptions = interviews.map((item) => ({ value: item.interview_id, label: `${item.interview_type} · ${new Date(item.scheduled_at).toLocaleString()}` }));

  return (
    <AppLayout>
      <div data-testid="ats-autonomy-root" className="min-h-full p-6 lg:p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <header className="grid gap-5 rounded-lg border border-indigo-500/20 bg-[radial-gradient(ellipse_at_85%_15%,rgba(45,212,191,0.13),transparent_38%),linear-gradient(120deg,#111827,#0b1120)] p-6 lg:grid-cols-[1.4fr_0.6fr] lg:items-end">
            <div><div className="font-mono2 text-[10px] tracking-[0.2em] text-teal-300">AUTONOMY STUDIO / GOVERNED RECOMMENDATIONS</div><h1 className="mt-2 font-display text-3xl font-black tracking-tight text-white">Intelligence can propose. Policy decides. People remain accountable.</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Every workflow builds a bounded plan from your organization’s ATS records. The runtime validates registered capabilities, evaluates policy, pauses for required approval, and records the trace.</p></div>
            <div className="grid grid-cols-3 gap-2"><Stat label="WORKFLOWS" value={WORKFLOW_DEFINITIONS.length} /><Stat label="PENDING REVIEW" value={approvals.length} /><Stat label="PLAN STEPS" value={plan?.steps?.length ?? 0} /></div>
          </header>

          {error && <div className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{typeof error === "string" ? error : "An unexpected request error occurred."}</div>}

          <main className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <section className="rounded-md border border-slate-800 bg-slate-900 p-4">
              <div className="mb-4 flex items-center gap-2"><Sparkles className="h-4 w-4 text-teal-300" /><div className="font-display text-lg font-black text-slate-100">Select a bounded workflow</div></div>
              <div className="space-y-2">{WORKFLOW_DEFINITIONS.map((item) => { const Icon = item.icon; const active = item.key === workflowKey; return <button key={item.key} onClick={() => { setWorkflowKey(item.key); setPlan(null); setExecution(null); setError(""); }} className={`w-full rounded-sm border p-3 text-left transition ${active ? item.tone : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:bg-slate-800/50"}`}><div className="flex items-center gap-3"><Icon className="h-4 w-4 shrink-0" /><div className="font-semibold text-sm text-slate-100">{item.label}</div><ChevronRight className="ml-auto h-4 w-4 opacity-50" /></div><p className="mt-1.5 pl-7 text-xs leading-5 text-slate-500">{item.description}</p></button>; })}</div>

              <div className="mt-5 rounded-sm border border-slate-800 bg-slate-950/60 p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500">CONTEXT FOR {workflow.label.toUpperCase()}</div>
                <div className="mt-3">
                  {workflow.entity === "requisition" && <Selector label="REQUISITION" value={requisitionId} onChange={setRequisitionId} options={requisitionOptions} emptyLabel="Choose a requisition" />}
                  {workflow.entity === "candidate" && <Selector label="CANDIDATE" value={candidateId} onChange={setCandidateId} options={candidateOptions} emptyLabel="Choose a candidate" />}
                  {workflow.entity === "application" && <Selector label="APPLICATION" value={applicationId} onChange={setApplicationId} options={applicationOptions} emptyLabel="Choose an application" />}
                  {workflow.entity === "interview" && <Selector label="INTERVIEW" value={interviewId} onChange={setInterviewId} options={interviewOptions} emptyLabel="Choose a scheduled interview" />}
                </div>
                <button disabled={!isReady || planning} onClick={planWorkflow} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2.5 text-sm font-bold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.98]">{planning ? <Loader2 className="h-4 w-4 animate-spin" /> : <BrainCircuit className="h-4 w-4" />}{planning ? "Building plan…" : "Request governed plan"}</button>
              </div>
              <div className="mt-4 rounded-sm border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between"><div className="font-mono2 text-[10px] tracking-widest text-slate-500">JOB DISTRIBUTION READINESS</div><span className="font-mono2 text-[10px] text-slate-600">{distributionAdapters.filter((adapter) => adapter.configuration_state === "connected").length}/{distributionAdapters.length} CONNECTED</span></div>
                <p className="mt-2 text-xs leading-5 text-slate-500">Providers remain non-operational until an administrator configures a connection. EAROS does not infer credentials or publish from a draft.</p>
                <div className="mt-3 grid gap-1.5 sm:grid-cols-2">{distributionAdapters.map((adapter) => <div key={adapter.adapter_id} className="flex items-center justify-between rounded-sm border border-slate-800 bg-slate-900/70 px-2.5 py-2"><span className="text-xs text-slate-300">{adapter.name}</span><span className={`font-mono2 text-[9px] tracking-wider ${adapter.configuration_state === "connected" ? "text-teal-300" : "text-slate-600"}`}>{adapter.configuration_state.replaceAll("_", " ")}</span></div>)}</div>
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900 p-5">
              <div className="flex items-center justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-slate-500">RECOMMENDATION REVIEW</div><h2 className="mt-1 font-display text-xl font-black text-slate-100">{plan ? plan.recommendation?.title || plan.goal : "No plan requested"}</h2></div><ShieldCheck className="h-6 w-6 text-indigo-300" /></div>
              {!plan ? <div className="mt-5 rounded-sm border border-dashed border-slate-700 bg-slate-950/50 p-8 text-center text-sm leading-6 text-slate-500">Choose a bounded workflow and factual record context. EAROS will return a reviewable plan rather than acting autonomously.</div> : <>
                <div className="mt-5 rounded-sm border border-slate-800 bg-slate-950/50 p-4"><div className="flex flex-wrap items-center gap-3"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">CONFIDENCE</span><span className="rounded-sm border border-teal-500/30 bg-teal-500/10 px-2 py-1 font-mono2 text-xs text-teal-200">{Math.round((plan.recommendation?.confidence?.value ?? plan.recommendation?.confidence ?? 0) * 100)}%</span><span className="ml-auto font-mono2 text-[10px] text-slate-600">PLAN {plan.plan_id}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{plan.recommendation?.summary}</p></div>
                <div className="mt-4 space-y-2">{plan.steps.map((step, index) => <div key={`${step.capability_id}-${index}`} className="flex gap-3 rounded-sm border border-slate-800 bg-slate-950/35 p-3"><div className="grid h-6 w-6 shrink-0 place-items-center rounded-sm bg-indigo-500/15 font-mono2 text-[10px] text-indigo-300">{index + 1}</div><div className="min-w-0"><div className="font-mono2 text-[11px] text-teal-300">{step.capability_id}</div><div className="mt-1 text-sm text-slate-200">{step.description}</div><pre className="mt-2 overflow-x-auto text-[10px] text-slate-500">{JSON.stringify(step.inputs, null, 2)}</pre></div></div>)}</div>
                {plan.steps.length === 0 ? <div className="mt-4 rounded-sm border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">No registered, valid step was proposed. Provide a more specific record context instead of attempting manual execution.</div> : <button disabled={executing} onClick={requestExecution} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-sm border border-indigo-400/50 bg-indigo-500/15 px-3 py-2.5 text-sm font-bold text-indigo-100 transition hover:bg-indigo-500/25 disabled:opacity-50">{executing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}{executing ? "Submitting to policy…" : "Submit reviewed plan to governed runtime"}</button>}
              </>}
              {execution && <div className="mt-4 rounded-sm border border-teal-500/30 bg-teal-500/10 p-4"><div className="flex items-center gap-2 font-semibold text-teal-100"><CheckCircle2 className="h-4 w-4" /> Runtime status: {execution.status}</div><div className="mt-2 font-mono2 text-[10px] text-teal-300">EXECUTION {execution.execution_id} · {execution.correlation_id}</div><p className="mt-2 text-xs leading-5 text-teal-100/70">If policy requires approval, EAROS has recorded a reviewable approval request rather than bypassing the control.</p></div>}
            </section>
          </main>
        </div>
      </div>
    </AppLayout>
  );
}
