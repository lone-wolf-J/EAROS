import React, { useMemo, useState } from "react";
import useSWR from "swr";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FolderHeart,
  Handshake,
  Plus,
  RefreshCw,
  Search,
  Send,
  Tags,
  UsersRound,
} from "lucide-react";
import { api } from "@/lib/api";
import AppLayout from "@/components/layout/AppLayout";
import { CareerIntakeManager, ReferralIntakeForm } from "@/components/CareerIntakeManager";

const fetcher = (url) => api.get(url).then((response) => response.data);

const TABS = [
  { key: "requisitions", label: "Requisitions", icon: BriefcaseBusiness },
  { key: "candidates", label: "Candidate CRM", icon: UsersRound },
  { key: "applications", label: "Applications", icon: ClipboardList },
  { key: "pools", label: "Talent pools", icon: FolderHeart },
  { key: "interviews", label: "Interviews", icon: CalendarDays },
  { key: "collaboration", label: "Collaboration", icon: UsersRound },
  { key: "distribution", label: "Distribution", icon: Send },
  { key: "offers", label: "Offers", icon: Handshake },
  { key: "handoffs", label: "Onboarding", icon: Handshake },
];

const COLLABORATION_GUARDRAILS = [
  "mentions_validate_tenant_users",
  "communications_are_recorded_not_delivered",
  "candidate_notifications_are_recorded_not_delivered",
  "outbound_email_and_sms_require_active_recruiting_consent",
];

const HIRING_DECISION_GUARDRAILS = [
  "final_outcomes_enter_governance_approval_queue",
  "requester_cannot_approve_or_deny_own_decision",
  "application_status_changes_only_after_independent_grant",
];

const OFFER_GUARDRAILS = [
  "offer_creation_is_an_internal_draft_only",
  "drafting_never_sends_or_extends_an_offer",
  "final_hire_outcomes_require_independent_decision_approval",
];

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function Status({ value }) {
  const normalized = String(value || "draft").replaceAll("_", " ");
  const styles = {
    open: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    active: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    scheduled: "border-violet-500/30 bg-violet-500/10 text-violet-300",
    pending_approval: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    awaiting_approval: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    effective: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    denied: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    ready_for_handoff: "border-teal-500/30 bg-teal-500/10 text-teal-300",
    acknowledged: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    draft: "border-slate-600/50 bg-slate-800 text-slate-300",
  };
  return (
    <span className={`inline-flex rounded-sm border px-1.5 py-0.5 font-mono2 text-[10px] tracking-wide ${styles[value] || styles.draft}`}>
      {normalized}
    </span>
  );
}

function EmptyState({ title, detail, onCreate }) {
  return (
    <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/60 px-6 py-12 text-center">
      <div className="font-display text-lg font-black text-slate-200">{title}</div>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{detail}</p>
      {onCreate && (
        <button onClick={onCreate} className="mt-5 inline-flex items-center gap-2 rounded-sm border border-indigo-500/50 bg-indigo-500/10 px-3 py-2 text-xs font-semibold text-indigo-200 transition hover:bg-indigo-500/20">
          <Plus className="h-3.5 w-3.5" /> Create record
        </button>
      )}
    </div>
  );
}

function Modal({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-slate-950/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-lg rounded-md border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <div className="font-mono2 text-[10px] tracking-[0.18em] text-indigo-400">EAROS / OPERATIONS</div>
            <h2 className="font-display text-xl font-black text-slate-100">{title}</h2>
          </div>
          <button onClick={onClose} className="rounded-sm px-2 py-1 text-sm text-slate-400 hover:bg-slate-800 hover:text-white">Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="font-mono2 text-[10px] tracking-widest text-slate-500">{label}</span>
      {children}
    </label>
  );
}

const inputClass = "w-full rounded-sm border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-700 focus:border-indigo-500";

function Metric({ label, value, detail, icon: Icon }) {
  return (
    <div className="relative overflow-hidden rounded-md border border-slate-800 bg-slate-900 p-4">
      <Icon className="absolute right-3 top-3 h-5 w-5 text-indigo-400/40" strokeWidth={1.5} />
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500">{label}</div>
      <div className="mt-1 font-display text-3xl font-black text-slate-100">{value ?? "—"}</div>
      <div className="mt-1 text-[11px] text-slate-500">{detail}</div>
    </div>
  );
}

export default function ATSOperations() {
  const [tab, setTab] = useState("requisitions");
  const [modal, setModal] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [crmQuery, setCrmQuery] = useState("");
  const [selectedCandidateIds, setSelectedCandidateIds] = useState([]);
  const [bulkAction, setBulkAction] = useState("add_tags");
  const [bulkTags, setBulkTags] = useState("");
  const [bulkSource, setBulkSource] = useState("");
  const [bulkPoolId, setBulkPoolId] = useState("");
  const [selectedInterviewId, setSelectedInterviewId] = useState("");
  const [selectedActivityCandidateId, setSelectedActivityCandidateId] = useState("");
  const [selectedDistributionRequisitionId, setSelectedDistributionRequisitionId] = useState("");
  const { data: requisitions = [], mutate: mutateRequisitions } = useSWR("/ats/requisitions", fetcher);
  const { data: pipelines = [] } = useSWR("/ats/pipelines", fetcher);
  const { data: applications = [], mutate: mutateApplications } = useSWR("/ats/applications", fetcher);
  const { data: pools = [], mutate: mutatePools } = useSWR("/ats/talent-pools", fetcher);
  const { data: interviews = [], mutate: mutateInterviews } = useSWR("/ats/interviews", fetcher);
  const { data: candidates = [], mutate: mutateCandidates } = useSWR("/world/candidates", fetcher);
  const crmPath = `/ats/candidates${crmQuery.trim() ? `?q=${encodeURIComponent(crmQuery.trim())}` : ""}`;
  const { data: crmCandidates = [], mutate: mutateCrmCandidates } = useSWR(crmPath, fetcher);
  const { data: candidateTags = [], mutate: mutateCandidateTags } = useSWR("/ats/candidate-tags", fetcher);
  const { data: scorecards = [], mutate: mutateScorecards } = useSWR("/ats/scorecards", fetcher);
  const { data: distributionAdapters = [] } = useSWR("/ats/job-distribution/adapters", fetcher);
  const feedbackPath = selectedInterviewId ? `/ats/interviews/${selectedInterviewId}/feedback` : null;
  const { data: interviewFeedback = [], mutate: mutateInterviewFeedback } = useSWR(feedbackPath, fetcher);
  const candidateActivityPath = selectedActivityCandidateId ? `/ats/activity/candidate/${selectedActivityCandidateId}` : null;
  const { data: candidateActivity = [], mutate: mutateCandidateActivity } = useSWR(candidateActivityPath, fetcher);
  const candidateMentionPath = selectedActivityCandidateId ? `/ats/candidates/${selectedActivityCandidateId}/collaboration/mentions` : null;
  const { data: candidateMentions = [], mutate: mutateCandidateMentions } = useSWR(candidateMentionPath, fetcher);
  const candidateCommunicationPath = selectedActivityCandidateId ? `/ats/candidates/${selectedActivityCandidateId}/communications` : null;
  const { data: candidateCommunications = [], mutate: mutateCandidateCommunications } = useSWR(candidateCommunicationPath, fetcher);
  const candidateNotificationPath = selectedActivityCandidateId ? `/ats/candidates/${selectedActivityCandidateId}/notification-deliveries` : null;
  const { data: candidateNotificationDeliveries = [], mutate: mutateCandidateNotificationDeliveries } = useSWR(candidateNotificationPath, fetcher);
  const { data: hiringDecisions = [], mutate: mutateHiringDecisions } = useSWR("/ats/hiring-decisions", fetcher);
  const { data: offers = [], mutate: mutateOffers } = useSWR("/ats/offers", fetcher);
  const { data: handoffs = [], mutate: mutateHandoffs } = useSWR("/ats/onboarding-handoffs", fetcher);

  const candidateById = useMemo(() => new Map(candidates.map((candidate) => [candidate.candidate_id, candidate])), [candidates]);
  const requisitionById = useMemo(() => new Map(requisitions.map((requisition) => [requisition.requisition_id, requisition])), [requisitions]);

  const refreshAll = () => Promise.all([mutateRequisitions(), mutateApplications(), mutatePools(), mutateInterviews(), mutateCandidates(), mutateCrmCandidates(), mutateCandidateTags(), mutateScorecards(), mutateInterviewFeedback(), mutateCandidateActivity(), mutateCandidateMentions(), mutateCandidateCommunications(), mutateCandidateNotificationDeliveries(), mutateHiringDecisions(), mutateOffers(), mutateHandoffs()]);
  const create = async (path, body, mutate) => {
    setError("");
    setSaving(true);
    try {
      await api.post(path, body);
      await mutate?.();
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : detail?.message || "EAROS could not save this record. Review the fields and try again.");
    } finally {
      setSaving(false);
    }
  };

  const runBulkAction = async () => {
    if (!selectedCandidateIds.length) {
      setError("Select one or more candidates before applying a CRM action.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await api.post("/ats/candidates/bulk", {
        candidate_ids: selectedCandidateIds,
        action: bulkAction,
        tags: bulkTags.split(",").map((tag) => tag.trim()).filter(Boolean),
        source: bulkSource || null,
        talent_pool_id: bulkPoolId || null,
      });
      setSelectedCandidateIds([]);
      await Promise.all([mutateCrmCandidates(), mutateCandidates(), mutatePools()]);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not apply the CRM action.");
    } finally {
      setSaving(false);
    }
  };

  const submitInterviewFeedback = async ({ interviewId, ...body }) => {
    setError("");
    setSaving(true);
    try {
      await api.post(`/ats/interviews/${interviewId}/feedback`, body);
      await Promise.all([mutateInterviewFeedback(), mutateCandidateActivity()]);
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not submit this structured feedback.");
    } finally {
      setSaving(false);
    }
  };

  const submitCandidateMention = async (body) => {
    if (!selectedActivityCandidateId) return;
    setError(""); setSaving(true);
    try {
      await api.post(`/ats/candidates/${selectedActivityCandidateId}/collaboration/mentions`, body);
      await Promise.all([mutateCandidateMentions(), mutateCandidateActivity()]);
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not record this collaboration mention.");
    } finally { setSaving(false); }
  };

  const recordCandidateCommunication = async (body) => {
    if (!selectedActivityCandidateId) return;
    setError(""); setSaving(true);
    try {
      await api.post(`/ats/candidates/${selectedActivityCandidateId}/communications`, body);
      await Promise.all([mutateCandidateCommunications(), mutateCandidateActivity()]);
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not record this candidate communication.");
    } finally { setSaving(false); }
  };

  const recordCandidateNotification = async (body) => {
    if (!selectedActivityCandidateId) return;
    setError(""); setSaving(true);
    try {
      await api.post(`/ats/candidates/${selectedActivityCandidateId}/notification-deliveries`, body);
      await Promise.all([mutateCandidateNotificationDeliveries(), mutateCandidateActivity()]);
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not record this candidate notification.");
    } finally { setSaving(false); }
  };

  const updatePublication = async (requisitionId, body) => {
    setError(""); setSaving(true);
    try { await api.patch(`/ats/requisitions/${requisitionId}/publication`, body); await mutateRequisitions(); }
    catch (requestError) { const detail = requestError?.response?.data?.detail; setError(typeof detail === "string" ? detail : "EAROS could not save requisition distribution readiness."); }
    finally { setSaving(false); }
  };

  const recordReferral = async (requisitionId, body) => {
    setError(""); setSaving(true);
    try {
      await api.post(`/ats/requisitions/${requisitionId}/referrals`, body);
      await Promise.all([mutateApplications(), mutateCandidates()]);
      setModal(null);
    } catch (requestError) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "EAROS could not record this referral. Confirm that referral intake is enabled and the referrer belongs to this organization.");
    } finally { setSaving(false); }
  };

  const openCounts = requisitions.filter((item) => item.approval_status === "open").length;
  const activeApplications = applications.filter((item) => item.status === "active").length;
  const scheduledInterviews = interviews.filter((item) => item.status === "scheduled").length;

  return (
    <AppLayout>
      <div data-testid="ats-operations-root" className="min-h-full p-6 lg:p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <section className="relative overflow-hidden rounded-lg border border-indigo-500/20 bg-[radial-gradient(ellipse_at_top_right,_rgba(79,70,229,0.18),transparent_55%),linear-gradient(110deg,_#111827,_#0f172a)] px-6 py-7">
            <div className="max-w-2xl">
              <div className="font-mono2 text-[10px] tracking-[0.2em] text-teal-300">ENTERPRISE ATS / HUMAN OPERATIONS</div>
              <h1 className="mt-2 font-display text-3xl font-black tracking-tight text-white sm:text-4xl">Recruiting workbench, governed by design.</h1>
              <p className="mt-3 text-sm leading-6 text-slate-400">Manage durable recruiting records while EAROS keeps agent recommendations, policy decisions, approvals, and auditable execution separated from human operations.</p>
            </div>
            <button onClick={refreshAll} className="absolute right-5 top-5 inline-flex items-center gap-2 rounded-sm border border-slate-700 bg-slate-950/70 px-3 py-2 font-mono2 text-[10px] tracking-wide text-slate-300 transition hover:border-indigo-500 hover:text-white">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </section>

          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Metric label="OPEN REQUISITIONS" value={openCounts} detail="approved requisitions" icon={BriefcaseBusiness} />
            <Metric label="ACTIVE APPLICANTS" value={activeApplications} detail="in tenant pipeline" icon={UsersRound} />
            <Metric label="TALENT POOLS" value={pools.length} detail="reusable prospects" icon={FolderHeart} />
            <Metric label="SCHEDULED" value={scheduledInterviews} detail={`${handoffs.length} handoff${handoffs.length === 1 ? "" : "s"} tracked`} icon={CalendarDays} />
          </section>

          {error && <div className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

          <section className="rounded-md border border-slate-800 bg-slate-900">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 pt-3">
              <div className="flex flex-wrap gap-1">
                {TABS.map(({ key, label, icon: Icon }) => (
                  <button key={key} onClick={() => setTab(key)} className={`inline-flex items-center gap-2 border-b-2 px-3 py-3 font-mono2 text-[11px] tracking-wide transition ${tab === key ? "border-teal-400 text-white" : "border-transparent text-slate-500 hover:text-slate-200"}`}>
                    <Icon className="h-3.5 w-3.5" /> {label}
                  </button>
                ))}
              </div>
              {tab !== "distribution" && <button onClick={() => setModal(tab === "requisitions" ? "requisition" : tab === "candidates" ? "candidate" : tab === "applications" ? "application" : tab === "pools" ? "pool" : tab === "interviews" ? "interview" : tab === "collaboration" ? "scorecard" : tab === "offers" ? "offer" : "handoff")} className="mb-2 inline-flex items-center gap-2 rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-xs font-bold text-white transition hover:brightness-110 active:scale-[0.98]">
                <Plus className="h-3.5 w-3.5" /> New {tab === "pools" ? "pool" : tab === "collaboration" ? "scorecard" : tab.slice(0, -1)}
              </button>}
            </div>

            <div className="p-4">
              {tab === "requisitions" && (requisitions.length ? (
                <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">
                  {requisitions.map((requisition) => (
                    <div key={requisition.requisition_id} className="grid gap-3 bg-slate-950/40 px-4 py-4 transition hover:bg-slate-800/30 md:grid-cols-[1.8fr_0.6fr_0.7fr_auto] md:items-center">
                      <div><div className="font-semibold text-slate-100">{requisition.title}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">{requisition.requisition_id} · {requisition.location || "Location pending"}</div></div>
                      <div><div className="font-mono2 text-[10px] text-slate-500">HEADCOUNT</div><div className="text-sm text-slate-200">{requisition.headcount}</div></div>
                      <div><div className="font-mono2 text-[10px] text-slate-500">PIPELINE</div><div className="text-sm text-slate-300">{pipelines.find((pipeline) => pipeline.pipeline_id === requisition.pipeline_id)?.name || "Default"}</div></div>
                      <Status value={requisition.approval_status} />
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="Open your first governed requisition" detail="Requisitions carry hiring-plan context and are the durable anchor for applications, interviews, and offer approvals." onCreate={() => setModal("requisition")} />)}

              {tab === "candidates" && <CandidateCRMWorkspace candidates={crmCandidates} tags={candidateTags} pools={pools} query={crmQuery} setQuery={setCrmQuery} selectedCandidateIds={selectedCandidateIds} setSelectedCandidateIds={setSelectedCandidateIds} bulkAction={bulkAction} setBulkAction={setBulkAction} bulkTags={bulkTags} setBulkTags={setBulkTags} bulkSource={bulkSource} setBulkSource={setBulkSource} bulkPoolId={bulkPoolId} setBulkPoolId={setBulkPoolId} saving={saving} onRunBulkAction={runBulkAction} onViewActivity={(candidateId) => { setSelectedActivityCandidateId(candidateId); setTab("collaboration"); }} />}

              {tab === "applications" && (applications.length ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  {applications.map((application) => {
                    const candidate = candidateById.get(application.candidate_id);
                    return <div key={application.application_id} className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="flex items-start justify-between gap-3"><div><div className="font-semibold text-slate-100">{candidate?.full_name || application.candidate_id}</div><div className="mt-1 text-xs text-slate-500">{requisitionById.get(application.requisition_id)?.title || "Unattached prospect"}</div></div><Status value={application.status} /></div><div className="mt-4 flex items-center gap-2 text-sm text-teal-300"><CheckCircle2 className="h-4 w-4" /> {application.current_stage_name}<ArrowRight className="ml-auto h-4 w-4 text-slate-600" /></div><div className="mt-3 font-mono2 text-[10px] text-slate-500">SOURCE · {application.source} · {formatDate(application.applied_at)}</div></div>;
                  })}
                </div>
              ) : <EmptyState title="No applications yet" detail="Create an application to connect a candidate to a requisition and preserve stage history, source attribution, score outputs, and audit context." onCreate={() => setModal("application")} />)}

              {tab === "pools" && (pools.length ? (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{pools.map((pool) => <div key={pool.talent_pool_id} className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="font-semibold text-slate-100">{pool.name}</div><p className="mt-2 min-h-10 text-sm text-slate-500">{pool.description || "No operating description recorded."}</p><div className="mt-4 flex flex-wrap gap-1">{(pool.tags || []).map((tag) => <span key={tag} className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-400">{tag}</span>)}</div><div className="mt-4 font-mono2 text-[10px] text-slate-600">{pool.talent_pool_id}</div></div>)}</div>
              ) : <EmptyState title="Create a reusable talent pool" detail="Keep consented prospects discoverable even before they apply to a specific requisition. Pool membership remains tenant-scoped and auditable." onCreate={() => setModal("pool")} />)}

              {tab === "interviews" && (interviews.length ? (
                <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">{interviews.map((interview) => <div key={interview.interview_id} className="flex flex-wrap items-center gap-4 bg-slate-950/40 px-4 py-4"><CalendarDays className="h-5 w-5 text-violet-300" /><div className="min-w-44 flex-1"><div className="font-semibold text-slate-100">{candidateById.get(interview.candidate_id)?.full_name || interview.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">{interview.interview_type} · {interview.duration_minutes} MIN · {interview.timezone}</div></div><div className="text-sm text-slate-300">{formatDate(interview.scheduled_at)}</div><Status value={interview.status} /><button type="button" onClick={() => { setSelectedInterviewId(interview.interview_id); setSelectedActivityCandidateId(interview.candidate_id); setTab("collaboration"); }} className="rounded-sm border border-indigo-500/40 px-2.5 py-1.5 text-xs font-semibold text-indigo-200 transition hover:bg-indigo-500/10">Review</button></div>)}</div>
              ) : <EmptyState title="No interviews scheduled" detail="Structured interview records connect schedule metadata, interviewer assignments, scorecards, and feedback without exposing an AI agent to ungoverned execution." onCreate={() => setModal("interview")} />)}

              {tab === "collaboration" && <div className="space-y-4"><CollaborationWorkspace interviews={interviews} candidates={candidates} scorecards={scorecards} feedback={interviewFeedback} selectedInterviewId={selectedInterviewId} setSelectedInterviewId={setSelectedInterviewId} selectedActivityCandidateId={selectedActivityCandidateId} setSelectedActivityCandidateId={setSelectedActivityCandidateId} activity={candidateActivity} mentions={candidateMentions} communications={candidateCommunications} onCreateScorecard={() => setModal("scorecard")} onSubmitFeedback={() => selectedInterviewId && setModal("feedback")} onCreateMention={() => selectedActivityCandidateId && setModal("mention")} onRecordCommunication={() => selectedActivityCandidateId && setModal("communication")} /><CandidateNotificationWorkspace candidates={candidates} selectedCandidateId={selectedActivityCandidateId} setSelectedCandidateId={setSelectedActivityCandidateId} deliveries={candidateNotificationDeliveries} onRecord={() => selectedActivityCandidateId && setModal("candidate-notification")} /><HiringDecisionWorkspace applications={applications} candidates={candidateById} decisions={hiringDecisions} onRequest={() => setModal("hiring-decision")} /></div>}

              {tab === "distribution" && <div className="space-y-4"><JobDistributionWorkspace requisitions={requisitions} adapters={distributionAdapters} selectedRequisitionId={selectedDistributionRequisitionId} setSelectedRequisitionId={setSelectedDistributionRequisitionId} saving={saving} onUpdatePublication={updatePublication} onRecordReferral={() => selectedDistributionRequisitionId && setModal("referral")} /><CareerIntakeManager requisitions={requisitions} selectedRequisitionId={selectedDistributionRequisitionId} onRecordReferral={() => selectedDistributionRequisitionId && setModal("referral")} /></div>}

              {tab === "offers" && <OfferWorkspace offers={offers} applications={applications} candidates={candidateById} onDraft={() => setModal("offer")} />}

              {tab === "handoffs" && (handoffs.length ? (
                <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">{handoffs.map((handoff) => <div key={handoff.onboarding_handoff_id} className="grid gap-3 bg-slate-950/40 px-4 py-4 transition hover:bg-slate-800/30 md:grid-cols-[1.6fr_1fr_auto] md:items-center"><div><div className="font-semibold text-slate-100">{candidateById.get(handoff.candidate_id)?.full_name || handoff.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">OFFER · {handoff.offer_id} · {handoff.destination_system || "Destination pending"}</div></div><div className="text-xs text-slate-400">START · {handoff.target_start_date || "Not scheduled"}<div className="mt-1 font-mono2 text-[10px] text-slate-600">{handoff.checklist?.length || 0} routing items</div></div><Status value={handoff.status} /></div>)}</div>
              ) : <EmptyState title="Handoff accepted hires with context, not secrets" detail="Create a minimal routing record from an accepted offer. Payroll, identity-provider credentials, and background-check files remain in the downstream onboarding system." onCreate={() => setModal("handoff")} />)}
            </div>
          </section>
        </div>

        {modal === "requisition" && <RequisitionForm pipelines={pipelines} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/requisitions", body, mutateRequisitions)} />}
        {modal === "candidate" && <CandidateForm saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/candidates", body, mutateCandidates)} />}
        {modal === "application" && <ApplicationForm candidates={candidates} requisitions={requisitions} pipelines={pipelines} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/applications", body, mutateApplications)} onCreateCandidate={() => setModal("candidate")} />}
        {modal === "referral" && <ReferralIntakeForm requisition={requisitionById.get(selectedDistributionRequisitionId)} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => recordReferral(selectedDistributionRequisitionId, body)} />}
        {modal === "pool" && <PoolForm saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/talent-pools", body, mutatePools)} />}
        {modal === "interview" && <InterviewForm applications={applications} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/interviews", body, mutateInterviews)} />}
        {modal === "scorecard" && <ScorecardForm requisitions={requisitions} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/scorecards", body, mutateScorecards)} />}
        {modal === "feedback" && <InterviewFeedbackForm interview={interviews.find((item) => item.interview_id === selectedInterviewId)} scorecards={scorecards} saving={saving} onClose={() => setModal(null)} onSubmit={submitInterviewFeedback} />}
        {modal === "mention" && <CollaborationMentionForm candidate={candidateById.get(selectedActivityCandidateId)} feedback={interviewFeedback} saving={saving} onClose={() => setModal(null)} onSubmit={submitCandidateMention} />}
        {modal === "communication" && <CandidateCommunicationForm candidate={candidateById.get(selectedActivityCandidateId)} saving={saving} onClose={() => setModal(null)} onSubmit={recordCandidateCommunication} />}
        {modal === "candidate-notification" && <CandidateNotificationForm candidate={candidateById.get(selectedActivityCandidateId)} saving={saving} onClose={() => setModal(null)} onSubmit={recordCandidateNotification} />}
        {modal === "hiring-decision" && <HiringDecisionForm applications={applications} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/hiring-decisions", body, mutateHiringDecisions)} />}
        {modal === "offer" && <OfferDraftForm applications={applications} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/offers", body, mutateOffers)} />}
        {modal === "handoff" && <HandoffForm offers={offers} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/onboarding-handoffs", body, mutateHandoffs)} />}
      </div>
    </AppLayout>
  );
}

function CandidateCRMWorkspace({ candidates, tags, pools, query, setQuery, selectedCandidateIds, setSelectedCandidateIds, bulkAction, setBulkAction, bulkTags, setBulkTags, bulkSource, setBulkSource, bulkPoolId, setBulkPoolId, saving, onRunBulkAction, onViewActivity }) {
  const selected = new Set(selectedCandidateIds);
  const toggleCandidate = (candidateId) => setSelectedCandidateIds((current) => current.includes(candidateId) ? current.filter((id) => id !== candidateId) : [...current, candidateId]);
  return <div className="space-y-4" data-testid="candidate-crm-workspace">
    <div className="grid gap-3 rounded-sm border border-slate-800 bg-slate-950/40 p-3 lg:grid-cols-[1.1fr_1fr]">
      <Field label="SEARCH ACTIVE TENANT CANDIDATES"><div className="relative"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" /><input value={query} onChange={(event) => setQuery(event.target.value)} className={`${inputClass} pl-9`} placeholder="Name, skill, title, source, or tag" /></div></Field>
      <div><div className="font-mono2 text-[10px] tracking-widest text-slate-500">AVAILABLE CUSTOM TAGS</div><div className="mt-2 flex min-h-10 flex-wrap gap-1.5">{tags.length ? tags.map((tag) => <span key={tag.candidate_tag_id} className="inline-flex items-center gap-1 rounded-sm border border-indigo-500/30 bg-indigo-500/10 px-2 py-1 font-mono2 text-[10px] text-indigo-200"><Tags className="h-3 w-3" /> {tag.name}</span>) : <span className="text-xs text-slate-500">No reusable tags created for this tenant.</span>}</div></div>
    </div>
    <div className="rounded-sm border border-teal-500/20 bg-teal-500/5 p-3">
      <div className="mb-3"><div className="font-mono2 text-[10px] tracking-widest text-teal-300">AUDITABLE BULK ACTION</div><div className="mt-1 text-xs text-slate-400">{selectedCandidateIds.length} selected. Every action records candidate activity and a governance event.</div></div>
      <div className="grid gap-2 md:grid-cols-4"><select value={bulkAction} onChange={(event) => setBulkAction(event.target.value)} className={inputClass}><option value="add_tags">Add tags</option><option value="remove_tags">Remove tags</option><option value="set_source">Set source</option><option value="add_to_talent_pool">Add to talent pool</option><option value="archive">Archive candidates</option></select>{["add_tags", "remove_tags"].includes(bulkAction) && <input value={bulkTags} onChange={(event) => setBulkTags(event.target.value)} className={inputClass} placeholder="Tags, comma-separated" />}{bulkAction === "set_source" && <input value={bulkSource} onChange={(event) => setBulkSource(event.target.value)} className={inputClass} placeholder="Source, e.g. referral" />}{bulkAction === "add_to_talent_pool" && <select value={bulkPoolId} onChange={(event) => setBulkPoolId(event.target.value)} className={inputClass}><option value="">Select pool</option>{pools.map((pool) => <option key={pool.talent_pool_id} value={pool.talent_pool_id}>{pool.name}</option>)}</select>}<button disabled={saving || !selectedCandidateIds.length} onClick={onRunBulkAction} className="rounded-sm border border-teal-400/40 bg-teal-400/10 px-3 py-2 text-xs font-bold text-teal-100 transition hover:bg-teal-400/20 disabled:cursor-not-allowed disabled:opacity-40">{saving ? "Applying…" : "Apply action"}</button></div>
    </div>
    {candidates.length ? <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">{candidates.map((candidate) => <div key={candidate.candidate_id} className="grid gap-3 bg-slate-950/40 px-4 py-4 transition hover:bg-slate-800/30 md:grid-cols-[auto_1.5fr_1fr_auto_auto] md:items-center"><input aria-label={`Select ${candidate.full_name}`} type="checkbox" checked={selected.has(candidate.candidate_id)} onChange={() => toggleCandidate(candidate.candidate_id)} className="h-4 w-4 accent-teal-400" /><div><div className="font-semibold text-slate-100">{candidate.full_name}</div><div className="mt-1 text-xs text-slate-500">{candidate.current_title || "Title pending"} · {candidate.current_company || "Company pending"}</div></div><div className="flex flex-wrap gap-1">{(candidate.tags || []).map((tag) => <span key={tag} className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-400">{tag}</span>)}</div><div className="text-right font-mono2 text-[10px] text-slate-500">SOURCE · {candidate.source}<br />FIT · {Math.round((candidate.fit_score || 0) * 100)}%</div><button type="button" onClick={() => onViewActivity(candidate.candidate_id)} className="rounded-sm border border-slate-700 px-2 py-1.5 text-xs font-semibold text-slate-300 transition hover:border-teal-400 hover:text-teal-200">Activity</button></div>)}</div> : <EmptyState title="No matching active candidates" detail="Search remains tenant-scoped and excludes archived records. Create a candidate or adjust the CRM query." />}
  </div>;
}

function CollaborationWorkspace({ interviews, candidates, scorecards, feedback, selectedInterviewId, setSelectedInterviewId, selectedActivityCandidateId, setSelectedActivityCandidateId, activity, mentions, communications, onCreateScorecard, onSubmitFeedback, onCreateMention, onRecordCommunication }) {
  const candidateById = new Map(candidates.map((candidate) => [candidate.candidate_id, candidate]));
  const selectedInterview = interviews.find((interview) => interview.interview_id === selectedInterviewId);
  return <div className="grid gap-4 xl:grid-cols-[0.95fr_1.25fr]" data-testid="collaboration-workspace">
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="flex items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-teal-300">STRUCTURED SCORECARDS</div><p className="mt-1 text-xs leading-5 text-slate-500">Competencies make evidence review comparable while keeping every interviewer’s recommendation independent.</p></div><button type="button" onClick={onCreateScorecard} className="rounded-sm border border-teal-400/40 px-2.5 py-1.5 text-xs font-bold text-teal-100 transition hover:bg-teal-400/10">New template</button></div><div className="mt-4 space-y-2">{scorecards.length ? scorecards.map((scorecard) => <div key={scorecard.scorecard_id} className="rounded-sm border border-slate-800 bg-slate-900/70 p-3"><div className="font-semibold text-slate-100">{scorecard.name}</div><div className="mt-2 flex flex-wrap gap-1">{scorecard.competencies.map((competency) => <span key={competency.name} className="rounded-sm border border-indigo-500/25 bg-indigo-500/10 px-1.5 py-0.5 font-mono2 text-[10px] text-indigo-200">{competency.name}</span>)}</div></div>) : <p className="rounded-sm border border-dashed border-slate-700 px-3 py-5 text-center text-xs text-slate-500">Create a scorecard template before collecting structured interviewer feedback.</p>}</div></section>
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="flex flex-wrap items-end justify-between gap-3"><Field label="INTERVIEW REVIEW"><select value={selectedInterviewId} onChange={(event) => { const interview = interviews.find((item) => item.interview_id === event.target.value); setSelectedInterviewId(event.target.value); if (interview) setSelectedActivityCandidateId(interview.candidate_id); }} className={`${inputClass} min-w-64`}><option value="">Select an interview</option>{interviews.map((interview) => <option key={interview.interview_id} value={interview.interview_id}>{candidateById.get(interview.candidate_id)?.full_name || interview.candidate_id} · {formatDate(interview.scheduled_at)}</option>)}</select></Field><button type="button" disabled={!selectedInterview} onClick={onSubmitFeedback} className="rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-xs font-bold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40">Submit feedback</button></div><div className="mt-4 space-y-3">{selectedInterview ? (feedback.length ? feedback.map((item) => <article key={item.feedback_id} className="rounded-sm border border-slate-800 bg-slate-900/70 p-3"><div className="flex items-start justify-between gap-3"><div><div className="font-semibold text-slate-100">{item.recommendation.replaceAll("_", " ")}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">INTERVIEWER · {item.interviewer_id} · {formatDate(item.submitted_at)}</div></div><Status value={item.recommendation} /></div>{item.summary && <p className="mt-3 text-sm leading-5 text-slate-400">{item.summary}</p>}<div className="mt-3 flex flex-wrap gap-1.5">{Object.entries(item.ratings || {}).map(([competency, rating]) => <span key={competency} className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-300">{competency}: {rating}/5</span>)}</div></article>) : <div className="rounded-sm border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-500">No feedback yet. Submit evidence before group debrief so independent signals remain auditable.</div>) : <div className="rounded-sm border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-500">Choose an interview to review submitted scorecards.</div>}</div></section>
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4 xl:col-span-2"><div className="flex flex-wrap items-end justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-teal-300">CANDIDATE ACTIVITY TIMELINE</div><p className="mt-1 text-xs text-slate-500">Append-only operational history is separate from the governance event stream and remains tenant-scoped.</p></div><Field label="CANDIDATE"><select value={selectedActivityCandidateId} onChange={(event) => setSelectedActivityCandidateId(event.target.value)} className={`${inputClass} min-w-64`}><option value="">Select a candidate</option>{candidates.map((candidate) => <option key={candidate.candidate_id} value={candidate.candidate_id}>{candidate.full_name}</option>)}</select></Field></div><div className="mt-4 space-y-2">{selectedActivityCandidateId ? (activity.length ? activity.map((item) => <div key={item.activity_id} className="grid gap-2 rounded-sm border border-slate-800 bg-slate-900/70 px-3 py-3 md:grid-cols-[0.85fr_1.5fr_0.65fr]"><div className="font-mono2 text-[10px] text-teal-300">{item.event_type.replaceAll("_", " ")}</div><div className="text-xs text-slate-400">{Object.entries(item.payload || {}).filter(([key]) => !["feedback_id", "scorecard_id"].includes(key)).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(" · ") || "Recorded operational event"}</div><div className="text-right font-mono2 text-[10px] text-slate-500">{formatDate(item.occurred_at)}</div></div>) : <div className="rounded-sm border border-dashed border-slate-700 px-4 py-6 text-center text-sm text-slate-500">No activity has been recorded for this candidate.</div>) : <div className="rounded-sm border border-dashed border-slate-700 px-4 py-6 text-center text-sm text-slate-500">Select a candidate to view immutable operational history.</div>}</div></section>
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4 xl:col-span-2"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-violet-300">COLLABORATION & CANDIDATE COMMUNICATIONS</div><p className="mt-1 text-xs leading-5 text-slate-500">Mentions validate tenant user references. Communications are human-recorded history only; this surface never sends email or SMS.</p></div><div className="flex gap-2"><button type="button" disabled={!selectedActivityCandidateId} onClick={onCreateMention} className="rounded-sm border border-violet-400/35 px-2.5 py-1.5 text-xs font-semibold text-violet-100 transition hover:bg-violet-500/10 disabled:cursor-not-allowed disabled:opacity-40">Mention teammate</button><button type="button" disabled={!selectedActivityCandidateId} onClick={onRecordCommunication} className="rounded-sm border border-teal-400/35 px-2.5 py-1.5 text-xs font-semibold text-teal-100 transition hover:bg-teal-400/10 disabled:cursor-not-allowed disabled:opacity-40">Record communication</button></div></div><div className="mt-4 grid gap-3 lg:grid-cols-2">{selectedActivityCandidateId ? <><div className="rounded-sm border border-slate-800 bg-slate-900/70 p-3"><div className="font-mono2 text-[10px] tracking-widest text-slate-500">MENTIONS</div><div className="mt-3 space-y-2">{mentions.length ? mentions.map((mention) => <div key={mention.mention_id} className="rounded-sm border border-slate-800 bg-slate-950/50 p-2.5"><div className="text-xs font-semibold text-slate-200">@{mention.mentioned_user_id}</div><div className="mt-1 text-xs leading-5 text-slate-500">{mention.context || "No additional context recorded."}</div><div className="mt-2 font-mono2 text-[9px] text-slate-600">{formatDate(mention.created_at)}</div></div>) : <p className="text-xs text-slate-500">No teammate references recorded for this candidate.</p>}</div></div><div className="rounded-sm border border-slate-800 bg-slate-900/70 p-3"><div className="font-mono2 text-[10px] tracking-widest text-slate-500">COMMUNICATION HISTORY</div><div className="mt-3 space-y-2">{communications.length ? communications.map((communication) => <div key={communication.communication_id} className="rounded-sm border border-slate-800 bg-slate-950/50 p-2.5"><div className="flex items-center justify-between gap-2"><div className="text-xs font-semibold text-slate-200">{communication.direction} · {communication.channel}</div><Status value={communication.delivery_state} /></div><div className="mt-1 text-xs text-slate-400">{communication.subject || communication.body || "Recorded communication"}</div><div className="mt-2 font-mono2 text-[9px] text-slate-600">{formatDate(communication.created_at)}</div></div>) : <p className="text-xs text-slate-500">No communications recorded. Consent is required for outbound email or SMS history.</p>}</div></div></> : <div className="rounded-sm border border-dashed border-slate-700 px-4 py-7 text-center text-sm text-slate-500 lg:col-span-2">Select a candidate before recording a mention or communication.</div>}</div></section>
  </div>;
}

function CandidateNotificationWorkspace({ candidates, selectedCandidateId, setSelectedCandidateId, deliveries, onRecord }) {
  return <section className="rounded-sm border border-amber-400/25 bg-amber-400/5 p-4" data-testid="candidate-notification-workspace"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-amber-200">CANDIDATE NOTIFICATION RECORDS</div><p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">Track notices related to application, interview, offer, or rejection. EAROS records intent and consent evidence but does not send email or SMS until a compliant delivery provider is configured.</p></div><button type="button" disabled={!selectedCandidateId} onClick={onRecord} className="rounded-sm border border-amber-400/35 bg-amber-400/10 px-2.5 py-1.5 text-xs font-bold text-amber-100 transition hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:opacity-40">Record candidate notice</button></div><div className="mt-4 grid gap-3 lg:grid-cols-[.85fr_1.15fr]"><Field label="CANDIDATE"><select value={selectedCandidateId} onChange={(event) => setSelectedCandidateId(event.target.value)} className={inputClass}><option value="">Select a candidate</option>{candidates.map((candidate) => <option key={candidate.candidate_id} value={candidate.candidate_id}>{candidate.full_name}</option>)}</select></Field><div className="rounded-sm border border-amber-400/20 bg-slate-950/45 px-3 py-2.5 text-xs leading-5 text-amber-50/75">Provider delivery is inactive by design. A <strong>not delivered</strong> status indicates an auditable record, not a completed external notification.</div></div><div className="mt-4 space-y-2">{selectedCandidateId ? (deliveries.length ? deliveries.map((delivery) => <article key={delivery.candidate_notification_delivery_id} className="grid gap-2 rounded-sm border border-slate-800 bg-slate-950/50 p-3 md:grid-cols-[1fr_auto]"><div><div className="font-semibold capitalize text-slate-100">{delivery.notification_type.replaceAll("_", " ")}</div><div className="mt-1 text-xs text-slate-400">{delivery.channel} · {delivery.subject || "Notification record"}</div><div className="mt-2 font-mono2 text-[9px] text-slate-600">{formatDate(delivery.created_at)} · CONSENT {delivery.consent_id || "NOT REQUIRED"}</div></div><Status value={delivery.delivery_state} /></article>) : <div className="rounded-sm border border-dashed border-amber-400/25 px-4 py-6 text-center text-xs text-slate-500">No candidate notifications have been recorded for this person.</div>) : <div className="rounded-sm border border-dashed border-amber-400/25 px-4 py-6 text-center text-xs text-slate-500">Select a candidate to inspect or record notification history.</div>}</div></section>;
}

function HiringDecisionWorkspace({ applications, candidates, decisions, onRequest }) {
  const activeApplications = applications.filter((application) => application.status === "active");
  return <section className="rounded-sm border border-amber-500/25 bg-amber-500/5 p-4" data-testid="hiring-decision-workspace"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-amber-300">GOVERNED HIRING DECISIONS</div><p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">Recruiters may request a final hire or reject outcome only after evidence review. EAROS creates a tenant-scoped approval request; an independent approver must decide it in Governance before the application state can change.</p></div><button type="button" disabled={!activeApplications.length} onClick={onRequest} className="rounded-sm border border-amber-400/40 bg-amber-400/10 px-2.5 py-1.5 text-xs font-bold text-amber-100 transition hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:opacity-40">Request decision review</button></div><div className="mt-4 space-y-2">{decisions.length ? decisions.map((decision) => <div key={decision.hiring_decision_id} className="grid gap-2 rounded-sm border border-slate-800 bg-slate-950/50 p-3 md:grid-cols-[1fr_auto]"><div><div className="font-semibold capitalize text-slate-100">{decision.outcome} · {candidates.get(decision.candidate_id)?.full_name || decision.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">APPLICATION · {decision.application_id} · REQUESTED {formatDate(decision.created_at)}</div><p className="mt-2 text-xs leading-5 text-slate-400">{decision.rationale}</p></div><div className="flex items-start justify-between gap-2 md:flex-col md:items-end"><Status value={decision.status} /><span className="font-mono2 text-[9px] text-slate-600">APPROVAL · {decision.approval_id || "PENDING"}</span></div></div>) : <div className="rounded-sm border border-dashed border-amber-500/25 px-4 py-6 text-center text-xs text-slate-500">No final outcome has been requested. Scorecard evidence remains independent until a human requests and approves a decision.</div>}</div></section>;
}

function OfferWorkspace({ offers, applications, candidates, onDraft }) {
  const activeApplications = applications.filter((application) => application.status === "active" && application.job_id);
  return <section className="space-y-4" data-testid="offer-workspace">
    <div className="rounded-sm border border-teal-400/25 bg-teal-400/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-teal-200">GOVERNED OFFER DRAFTS</div><p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">Prepare an internal compensation record for an active application. Creating a draft does not send, extend, accept, or approve an offer. A final hire outcome remains in the independent decision-review flow.</p></div><button type="button" disabled={!activeApplications.length} onClick={onDraft} className="rounded-sm border border-teal-400/35 bg-teal-400/10 px-2.5 py-1.5 text-xs font-bold text-teal-100 transition hover:bg-teal-400/20 disabled:cursor-not-allowed disabled:opacity-40">Draft offer</button></div>
      <div className="mt-4 rounded-sm border border-teal-400/20 bg-slate-950/45 px-3 py-2.5 text-xs leading-5 text-teal-50/75">No candidate communication, e-signature, payroll routing, or final status mutation occurs here. EAROS records a tenant-scoped internal draft and its audit event only.</div>
    </div>
    <div className="space-y-2">{offers.length ? offers.map((offer) => <article key={offer.offer_id} className="grid gap-3 rounded-sm border border-slate-800 bg-slate-950/40 p-4 md:grid-cols-[1fr_auto]"><div><div className="font-semibold text-slate-100">{candidates.get(offer.candidate_id)?.full_name || offer.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">JOB · {offer.job_id} · OFFER {offer.offer_id}</div><div className="mt-3 flex flex-wrap gap-1.5"><span className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-300">BASE · {offer.currency} {Number(offer.base_salary || 0).toLocaleString()}</span>{Number(offer.bonus || 0) > 0 && <span className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-300">BONUS · {offer.currency} {Number(offer.bonus).toLocaleString()}</span>}{Number(offer.equity_units || 0) > 0 && <span className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[10px] text-slate-300">EQUITY · {Number(offer.equity_units).toLocaleString()}</span>}</div></div><div className="flex items-start justify-between gap-2 md:flex-col md:items-end"><Status value={offer.status} /><span className="font-mono2 text-[9px] text-slate-600">RECORDED {formatDate(offer.created_at)}</span></div></article>) : <EmptyState title="No internal offer drafts" detail="Select an active application to record a reviewable compensation draft. Offer delivery remains inactive." onCreate={activeApplications.length ? onDraft : undefined} />}</div>
  </section>;
}

function OfferDraftForm({ applications, candidates, saving, onClose, onSubmit }) {
  const eligible = applications.filter((application) => application.status === "active" && application.job_id);
  const [applicationId, setApplicationId] = useState(eligible[0]?.application_id || "");
  const [baseSalary, setBaseSalary] = useState("");
  const [bonus, setBonus] = useState("0");
  const [equityUnits, setEquityUnits] = useState("0");
  const [signingBonus, setSigningBonus] = useState("0");
  const [currency, setCurrency] = useState("USD");
  const application = eligible.find((item) => item.application_id === applicationId);
  return <Modal title="Draft internal offer" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); if (application) onSubmit({ candidate_id: application.candidate_id, job_id: application.job_id, base_salary: Number(baseSalary), bonus: Number(bonus || 0), equity_units: Number(equityUnits || 0), signing_bonus: Number(signingBonus || 0), currency: currency.toUpperCase() }); }} className="space-y-4 p-5"><p className="rounded-sm border border-teal-400/20 bg-teal-400/5 px-3 py-2.5 text-xs leading-5 text-teal-50/75">This records an internal draft only. It does not send an offer, contact a candidate, modify a final application status, or replace independent decision approval.</p><Field label="ACTIVE APPLICATION"><select required value={applicationId} onChange={(event) => setApplicationId(event.target.value)} className={inputClass}><option value="">Select an active application</option>{eligible.map((item) => <option key={item.application_id} value={item.application_id}>{candidates.get(item.candidate_id)?.full_name || item.candidate_id} · {item.current_stage_name}</option>)}</select></Field><div className="grid gap-3 sm:grid-cols-2"><Field label="BASE SALARY"><input className={inputClass} required min="0" type="number" value={baseSalary} onChange={(event) => setBaseSalary(event.target.value)} /></Field><Field label="CURRENCY"><input className={inputClass} required maxLength="3" pattern="[A-Za-z]{3}" value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} /></Field><Field label="BONUS"><input className={inputClass} min="0" type="number" value={bonus} onChange={(event) => setBonus(event.target.value)} /></Field><Field label="SIGNING BONUS"><input className={inputClass} min="0" type="number" value={signingBonus} onChange={(event) => setSigningBonus(event.target.value)} /></Field><Field label="EQUITY UNITS"><input className={inputClass} min="0" type="number" value={equityUnits} onChange={(event) => setEquityUnits(event.target.value)} /></Field></div><div className="flex justify-end gap-2 border-t border-slate-800 pt-4"><button type="button" onClick={onClose} className="rounded-sm px-3 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800">Cancel</button><button disabled={saving || !application || !baseSalary} className="rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Saving…" : "Record offer draft"}</button></div></form></Modal>;
}

function JobDistributionWorkspace({ requisitions, adapters, selectedRequisitionId, setSelectedRequisitionId, saving, onUpdatePublication, onRecordReferral }) {
  const requisition = requisitions.find((item) => item.requisition_id === selectedRequisitionId);
  const targets = requisition?.external_publication_targets || [];
  const careerSitePath = requisition ? `/careers?org=${encodeURIComponent(requisition.organization_id)}` : "";
  const toggleProvider = (provider) => onUpdatePublication(requisition.requisition_id, { external_publication_targets: targets.includes(provider) ? targets.filter((item) => item !== provider) : [...targets, provider] });
  return <div className="grid gap-4 xl:grid-cols-[0.9fr_1.4fr]" data-testid="job-distribution-workspace">
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="font-mono2 text-[10px] tracking-widest text-teal-300">PUBLICATION CONTROL</div><p className="mt-2 text-sm leading-6 text-slate-400">Set internal career-site readiness and prepare external targets. No click on this page publishes to a job board; external delivery remains draft-only until a provider is configured and a human approval is recorded.</p><Field label="REQUISITION"><select value={selectedRequisitionId} onChange={(event) => setSelectedRequisitionId(event.target.value)} className={`${inputClass} mt-4`}><option value="">Select a requisition</option>{requisitions.map((item) => <option key={item.requisition_id} value={item.requisition_id}>{item.title}</option>)}</select></Field>{requisition && <div className="mt-4 space-y-4"><div><div className="mb-2 font-mono2 text-[10px] tracking-wider text-slate-500">INTERNAL CAREER SITE</div><div className="flex flex-wrap gap-2">{["draft", "published", "closed"].map((status) => <button type="button" key={status} disabled={saving} onClick={() => onUpdatePublication(requisition.requisition_id, { internal_publication_status: status })} className={`rounded-sm border px-2.5 py-1.5 text-xs font-semibold transition ${requisition.internal_publication_status === status ? "border-teal-400/45 bg-teal-400/10 text-teal-100" : "border-slate-700 text-slate-400 hover:text-slate-200"}`}>{status}</button>)}</div></div><label className="flex items-center justify-between gap-3 rounded-sm border border-slate-800 bg-slate-900/60 px-3 py-2.5 text-sm text-slate-300"><span>Enable career-site application intake</span><input aria-label="Enable career-site application intake" type="checkbox" checked={Boolean(requisition.career_site_enabled)} disabled={saving} onChange={(event) => onUpdatePublication(requisition.requisition_id, { career_site_enabled: event.target.checked })} className="h-4 w-4 accent-teal-400" /></label><label className="flex items-center justify-between gap-3 rounded-sm border border-slate-800 bg-slate-900/60 px-3 py-2.5 text-sm text-slate-300"><span>Accept employee referrals</span><input aria-label="Accept employee referrals" type="checkbox" checked={Boolean(requisition.referral_intake_enabled)} disabled={saving} onChange={(event) => onUpdatePublication(requisition.requisition_id, { referral_intake_enabled: event.target.checked })} className="h-4 w-4 accent-teal-400" /></label></div>}</section>
    <section className="rounded-sm border border-slate-800 bg-slate-950/40 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="font-mono2 text-[10px] tracking-widest text-violet-300">EXTERNAL DISTRIBUTION READINESS</div><p className="mt-1 text-xs leading-5 text-slate-500">The catalog exposes provider requirements only. EAROS never infers a provider connection from a selected target.</p></div>{requisition && <button type="button" disabled={saving || !targets.length} onClick={() => onUpdatePublication(requisition.requisition_id, { external_publication_status: "pending_approval", external_publication_targets: targets })} className="rounded-sm border border-amber-400/35 bg-amber-400/10 px-2.5 py-1.5 text-xs font-bold text-amber-100 disabled:cursor-not-allowed disabled:opacity-40">Queue draft for review</button>}</div>{requisition && <div className="mt-3 rounded-sm border border-indigo-500/20 bg-indigo-500/5 px-3 py-2 font-mono2 text-[10px] text-indigo-100">EXTERNAL STATE · {requisition.external_publication_status || "not_requested"}</div>}<div className="mt-4 space-y-2">{adapters.map((adapter) => <div key={adapter.adapter_id} className="flex flex-col gap-3 rounded-sm border border-slate-800 bg-slate-900/60 p-3 md:flex-row md:items-center"><input aria-label={`Target ${adapter.name}`} type="checkbox" checked={targets.includes(adapter.provider)} disabled={!requisition || saving} onChange={() => toggleProvider(adapter.provider)} className="h-4 w-4 accent-violet-400" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-slate-100">{adapter.name}</span><span className="rounded-sm border border-slate-700 px-1.5 py-0.5 font-mono2 text-[9px] text-slate-500">{adapter.configuration_state}</span></div><p className="mt-1 text-xs leading-5 text-slate-500">{adapter.notes}</p></div><div className="font-mono2 text-[9px] text-slate-600">APPROVAL · {adapter.requires_human_approval ? "REQUIRED" : "NOT REQUIRED"}</div></div>)}</div></section>
  </div>;
}

function FormActions({ saving, onClose, label }) { return <div className="flex justify-end gap-2 border-t border-slate-800 px-5 py-4"><button type="button" onClick={onClose} className="rounded-sm px-3 py-2 text-sm text-slate-400 hover:bg-slate-800">Cancel</button><button disabled={saving} className="rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-sm font-bold text-white disabled:cursor-wait disabled:opacity-60">{saving ? "Saving…" : label}</button></div>; }

function HiringDecisionForm({ applications, candidates, saving, onClose, onSubmit }) {
  const [applicationId, setApplicationId] = useState(""); const [outcome, setOutcome] = useState("hire"); const [rationale, setRationale] = useState("");
  const activeApplications = applications.filter((application) => application.status === "active");
  return <Modal title="Request hiring decision review" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ application_id: applicationId, outcome, rationale }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-amber-400/25 bg-amber-400/5 px-3 py-2 text-xs leading-5 text-amber-100">This request cannot directly hire or reject a candidate. It enters the EAROS Governance queue, and the requester cannot approve or deny their own decision.</div><Field label="ACTIVE APPLICATION"><select required value={applicationId} onChange={(event) => setApplicationId(event.target.value)} className={inputClass}><option value="">Select an active application</option>{activeApplications.map((application) => <option key={application.application_id} value={application.application_id}>{candidates.get(application.candidate_id)?.full_name || application.candidate_id} · {application.current_stage_name}</option>)}</select></Field><Field label="PROPOSED OUTCOME"><select value={outcome} onChange={(event) => setOutcome(event.target.value)} className={inputClass}><option value="hire">Hire</option><option value="reject">Reject</option></select></Field><Field label="EVIDENCE-BASED RATIONALE"><textarea required minLength="10" value={rationale} onChange={(event) => setRationale(event.target.value)} className={`${inputClass} min-h-28 resize-y`} placeholder="Summarize the job-related evidence and panel review supporting this request." /></Field></div><FormActions saving={saving} onClose={onClose} label="Queue for approval" /></form></Modal>;
}

function RequisitionForm({ pipelines, saving, onClose, onSubmit }) {
  const [title, setTitle] = useState(""); const [headcount, setHeadcount] = useState(1); const [location, setLocation] = useState(""); const [pipelineId, setPipelineId] = useState("");
  return <Modal title="New requisition" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ title, headcount: Number(headcount), location: location || null, pipeline_id: pipelineId || null }); }}><div className="grid gap-4 px-5 py-5"><Field label="ROLE TITLE"><input required value={title} onChange={(event) => setTitle(event.target.value)} className={inputClass} placeholder="e.g. Senior Product Designer" /></Field><div className="grid grid-cols-2 gap-3"><Field label="HEADCOUNT"><input required type="number" min="1" value={headcount} onChange={(event) => setHeadcount(event.target.value)} className={inputClass} /></Field><Field label="LOCATION"><input value={location} onChange={(event) => setLocation(event.target.value)} className={inputClass} placeholder="Remote / city" /></Field></div><Field label="PIPELINE"><select value={pipelineId} onChange={(event) => setPipelineId(event.target.value)} className={inputClass}><option value="">Use default pipeline</option>{pipelines.map((pipeline) => <option key={pipeline.pipeline_id} value={pipeline.pipeline_id}>{pipeline.name}</option>)}</select></Field></div><FormActions saving={saving} onClose={onClose} label="Create requisition" /></form></Modal>;
}

function CandidateForm({ saving, onClose, onSubmit }) {
  const [fullName, setFullName] = useState(""); const [email, setEmail] = useState(""); const [currentTitle, setCurrentTitle] = useState("");
  return <Modal title="New candidate" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ full_name: fullName, email: email || null, current_title: currentTitle }); }}><div className="grid gap-4 px-5 py-5"><Field label="FULL NAME"><input required value={fullName} onChange={(event) => setFullName(event.target.value)} className={inputClass} /></Field><Field label="EMAIL"><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} placeholder="candidate@example.com" /></Field><Field label="CURRENT TITLE"><input value={currentTitle} onChange={(event) => setCurrentTitle(event.target.value)} className={inputClass} placeholder="Optional" /></Field></div><FormActions saving={saving} onClose={onClose} label="Create candidate" /></form></Modal>;
}

function ApplicationForm({ candidates, requisitions, pipelines, saving, onClose, onSubmit, onCreateCandidate }) {
  const [candidateId, setCandidateId] = useState(""); const [requisitionId, setRequisitionId] = useState(""); const [pipelineId, setPipelineId] = useState("");
  return <Modal title="New application" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ candidate_id: candidateId, requisition_id: requisitionId || null, pipeline_id: pipelineId || null }); }}><div className="grid gap-4 px-5 py-5"><Field label="CANDIDATE"><select required value={candidateId} onChange={(event) => setCandidateId(event.target.value)} className={inputClass}><option value="">Select a candidate</option>{candidates.map((candidate) => <option key={candidate.candidate_id} value={candidate.candidate_id}>{candidate.full_name}</option>)}</select></Field>{!candidates.length && <button type="button" onClick={onCreateCandidate} className="text-left text-xs text-teal-300 hover:text-teal-200">Create a candidate first →</button>}<Field label="REQUISITION"><select value={requisitionId} onChange={(event) => setRequisitionId(event.target.value)} className={inputClass}><option value="">Unattached prospect</option>{requisitions.map((requisition) => <option key={requisition.requisition_id} value={requisition.requisition_id}>{requisition.title}</option>)}</select></Field><Field label="PIPELINE"><select value={pipelineId} onChange={(event) => setPipelineId(event.target.value)} className={inputClass}><option value="">Use requisition/default workflow</option>{pipelines.map((pipeline) => <option key={pipeline.pipeline_id} value={pipeline.pipeline_id}>{pipeline.name}</option>)}</select></Field></div><FormActions saving={saving} onClose={onClose} label="Create application" /></form></Modal>;
}

function PoolForm({ saving, onClose, onSubmit }) { const [name, setName] = useState(""); const [description, setDescription] = useState(""); return <Modal title="New talent pool" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ name, description: description || null }); }}><div className="grid gap-4 px-5 py-5"><Field label="POOL NAME"><input required value={name} onChange={(event) => setName(event.target.value)} className={inputClass} placeholder="e.g. Product leadership" /></Field><Field label="OPERATING PURPOSE"><textarea value={description} onChange={(event) => setDescription(event.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="Who belongs here and when should recruiters use it?" /></Field></div><FormActions saving={saving} onClose={onClose} label="Create talent pool" /></form></Modal>; }

function InterviewForm({ applications, candidates, saving, onClose, onSubmit }) { const [applicationId, setApplicationId] = useState(""); const [scheduledAt, setScheduledAt] = useState(""); return <Modal title="Schedule interview" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); const application = applications.find((item) => item.application_id === applicationId); onSubmit({ application_id: applicationId, candidate_id: application?.candidate_id, scheduled_at: new Date(scheduledAt).toISOString() }); }}><div className="grid gap-4 px-5 py-5"><Field label="APPLICATION"><select required value={applicationId} onChange={(event) => setApplicationId(event.target.value)} className={inputClass}><option value="">Select an application</option>{applications.map((application) => <option key={application.application_id} value={application.application_id}>{candidates.get(application.candidate_id)?.full_name || application.candidate_id} · {application.current_stage_name}</option>)}</select></Field><Field label="SCHEDULED TIME"><input required type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} className={inputClass} /></Field></div><FormActions saving={saving} onClose={onClose} label="Schedule interview" /></form></Modal>; }

function ScorecardForm({ requisitions, saving, onClose, onSubmit }) {
  const [name, setName] = useState(""); const [requisitionId, setRequisitionId] = useState(""); const [competencies, setCompetencies] = useState("");
  return <Modal title="New scorecard template" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ name, requisition_id: requisitionId || null, competencies: competencies.split(",").map((item) => item.trim()).filter(Boolean).map((item) => ({ name: item })) }); }}><div className="grid gap-4 px-5 py-5"><Field label="TEMPLATE NAME"><input required value={name} onChange={(event) => setName(event.target.value)} className={inputClass} placeholder="e.g. Product leadership interview" /></Field><Field label="REQUISITION"><select value={requisitionId} onChange={(event) => setRequisitionId(event.target.value)} className={inputClass}><option value="">Reusable across requisitions</option>{requisitions.map((requisition) => <option key={requisition.requisition_id} value={requisition.requisition_id}>{requisition.title}</option>)}</select></Field><Field label="COMPETENCIES"><input required value={competencies} onChange={(event) => setCompetencies(event.target.value)} className={inputClass} placeholder="Role evidence, collaboration, judgment" /><p className="text-xs leading-5 text-slate-500">Use commas to define independently rated dimensions. EAROS stores the template and never generates hiring feedback.</p></Field></div><FormActions saving={saving} onClose={onClose} label="Create scorecard" /></form></Modal>;
}

function InterviewFeedbackForm({ interview, scorecards, saving, onClose, onSubmit }) {
  const [scorecardId, setScorecardId] = useState(""); const [recommendation, setRecommendation] = useState("abstain"); const [ratings, setRatings] = useState({}); const [strengths, setStrengths] = useState(""); const [concerns, setConcerns] = useState(""); const [summary, setSummary] = useState("");
  const scorecard = scorecards.find((item) => item.scorecard_id === scorecardId);
  if (!interview) return null;
  return <Modal title="Submit structured feedback" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ interviewId: interview.interview_id, scorecard_id: scorecardId || null, recommendation, ratings: Object.fromEntries(Object.entries(ratings).filter(([, value]) => value !== "" && Number(value) > 0).map(([key, value]) => [key, Number(value)])), strengths: strengths.split("\n").map((item) => item.trim()).filter(Boolean), concerns: concerns.split("\n").map((item) => item.trim()).filter(Boolean), summary: summary || null }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-indigo-500/20 bg-indigo-500/5 px-3 py-2 text-xs text-indigo-100">Submit your evidence independently. EAROS records your recommendation and audit event; it does not make the hiring decision.</div><Field label="SCORECARD TEMPLATE"><select value={scorecardId} onChange={(event) => { setScorecardId(event.target.value); setRatings({}); }} className={inputClass}><option value="">No template / narrative feedback</option>{scorecards.map((item) => <option key={item.scorecard_id} value={item.scorecard_id}>{item.name}</option>)}</select></Field>{scorecard?.competencies?.map((competency) => <Field key={competency.name} label={`${competency.name.toUpperCase()} · 1–5`}><input type="number" min="1" max="5" value={ratings[competency.name] || ""} onChange={(event) => setRatings((current) => ({ ...current, [competency.name]: event.target.value }))} className={inputClass} placeholder="Rating" /></Field>)}<Field label="RECOMMENDATION"><select value={recommendation} onChange={(event) => setRecommendation(event.target.value)} className={inputClass}><option value="strong_yes">Strong yes</option><option value="yes">Yes</option><option value="abstain">Abstain</option><option value="no">No</option><option value="strong_no">Strong no</option></select></Field><Field label="EVIDENCE SUMMARY"><textarea value={summary} onChange={(event) => setSummary(event.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="Ground recommendation in observed evidence, not assumptions." /></Field><div className="grid gap-3 md:grid-cols-2"><Field label="STRENGTHS · ONE PER LINE"><textarea value={strengths} onChange={(event) => setStrengths(event.target.value)} className={`${inputClass} min-h-20 resize-y`} /></Field><Field label="CONCERNS · ONE PER LINE"><textarea value={concerns} onChange={(event) => setConcerns(event.target.value)} className={`${inputClass} min-h-20 resize-y`} /></Field></div></div><FormActions saving={saving} onClose={onClose} label="Submit feedback" /></form></Modal>;
}

function CollaborationMentionForm({ candidate, feedback, saving, onClose, onSubmit }) {
  const [mentionedUserId, setMentionedUserId] = useState(""); const [feedbackId, setFeedbackId] = useState(""); const [context, setContext] = useState("");
  return <Modal title="Mention a teammate" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ mentioned_user_id: mentionedUserId, feedback_id: feedbackId || null, context: context || null }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-violet-500/20 bg-violet-500/5 px-3 py-2 text-xs leading-5 text-violet-100">Mention targets must be provisioned in this EAROS organization. The record is appended to {candidate?.full_name || "the selected candidate"}&rsquo;s activity history.</div><Field label="TENANT USER ID"><input required value={mentionedUserId} onChange={(event) => setMentionedUserId(event.target.value)} className={inputClass} placeholder="e.g. user_…" /></Field><Field label="RELATED FEEDBACK (OPTIONAL)"><select value={feedbackId} onChange={(event) => setFeedbackId(event.target.value)} className={inputClass}><option value="">No feedback link</option>{feedback.map((item) => <option key={item.feedback_id} value={item.feedback_id}>{item.recommendation.replaceAll("_", " ")} · {item.feedback_id}</option>)}</select></Field><Field label="CONTEXT"><textarea value={context} onChange={(event) => setContext(event.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="What should the teammate review?" /></Field></div><FormActions saving={saving} onClose={onClose} label="Record mention" /></form></Modal>;
}

function CandidateCommunicationForm({ candidate, saving, onClose, onSubmit }) {
  const [direction, setDirection] = useState("outbound"); const [channel, setChannel] = useState("email"); const [subject, setSubject] = useState(""); const [body, setBody] = useState("");
  return <Modal title="Record candidate communication" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ direction, channel, subject: subject || null, body: body || null }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-teal-500/20 bg-teal-500/5 px-3 py-2 text-xs leading-5 text-teal-100">This creates an immutable communication history record for {candidate?.full_name || "the selected candidate"}; it does not deliver a message. EAROS requires active recruiting consent for outbound email or SMS records.</div><div className="grid grid-cols-2 gap-3"><Field label="DIRECTION"><select value={direction} onChange={(event) => setDirection(event.target.value)} className={inputClass}><option value="outbound">Outbound</option><option value="inbound">Inbound</option></select></Field><Field label="CHANNEL"><select value={channel} onChange={(event) => setChannel(event.target.value)} className={inputClass}><option value="email">Email</option><option value="phone">Phone</option><option value="sms">SMS</option><option value="in_app">In-app</option><option value="other">Other</option></select></Field></div><Field label="SUBJECT"><input value={subject} onChange={(event) => setSubject(event.target.value)} className={inputClass} placeholder="e.g. Interview scheduling update" /></Field><Field label="SUMMARY OR RECORD"><textarea value={body} onChange={(event) => setBody(event.target.value)} className={`${inputClass} min-h-28 resize-y`} placeholder="Record the human communication with only the necessary recruiting context." /></Field></div><FormActions saving={saving} onClose={onClose} label="Record communication" /></form></Modal>;
}

function CandidateNotificationForm({ candidate, saving, onClose, onSubmit }) {
  const [notificationType, setNotificationType] = useState("application_received"); const [channel, setChannel] = useState("email"); const [subject, setSubject] = useState(""); const [body, setBody] = useState("");
  return <Modal title="Record candidate notification" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); onSubmit({ notification_type: notificationType, channel, subject: subject || null, body: body || null }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-amber-400/25 bg-amber-400/5 px-3 py-2 text-xs leading-5 text-amber-100">This records a notification intent for {candidate?.full_name || "the selected candidate"}. No email, SMS, or other external provider call occurs. Active recruiting consent is required for email and SMS records.</div><div className="grid grid-cols-2 gap-3"><Field label="NOTICE TYPE"><select value={notificationType} onChange={(event) => setNotificationType(event.target.value)} className={inputClass}><option value="application_received">Application received</option><option value="interview_scheduled">Interview scheduled</option><option value="offer_update">Offer update</option><option value="rejection_update">Rejection update</option><option value="general_update">General update</option></select></Field><Field label="INTENDED CHANNEL"><select value={channel} onChange={(event) => setChannel(event.target.value)} className={inputClass}><option value="email">Email</option><option value="sms">SMS</option><option value="in_app">In-app</option><option value="other">Other</option></select></Field></div><Field label="SUBJECT"><input value={subject} onChange={(event) => setSubject(event.target.value)} className={inputClass} placeholder="e.g. Your EAROS application update" /></Field><Field label="RECORD SUMMARY"><textarea value={body} onChange={(event) => setBody(event.target.value)} className={`${inputClass} min-h-28 resize-y`} placeholder="Record the approved candidate-facing notification context." /></Field></div><FormActions saving={saving} onClose={onClose} label="Record notification" /></form></Modal>;
}

function HandoffForm({ offers, candidates, saving, onClose, onSubmit }) {
  const [offerId, setOfferId] = useState(""); const [destinationSystem, setDestinationSystem] = useState(""); const [targetStartDate, setTargetStartDate] = useState("");
  const acceptedOffers = offers.filter((offer) => offer.status === "accepted");
  return <Modal title="Create onboarding handoff" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); const offer = acceptedOffers.find((item) => item.offer_id === offerId); if (!offer) return; onSubmit({ offer_id: offer.offer_id, candidate_id: offer.candidate_id, job_id: offer.job_id, destination_system: destinationSystem || null, target_start_date: targetStartDate || null, checklist: [] }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-teal-500/20 bg-teal-500/5 px-3 py-2 text-xs leading-5 text-teal-100">Only accepted offers can transfer. This record routes work; it deliberately never stores payroll, credentials, or background-check documents.</div><Field label="ACCEPTED OFFER"><select required value={offerId} onChange={(event) => setOfferId(event.target.value)} className={inputClass}><option value="">Select an accepted offer</option>{acceptedOffers.map((offer) => <option key={offer.offer_id} value={offer.offer_id}>{candidates.get(offer.candidate_id)?.full_name || offer.candidate_id} · {offer.offer_id}</option>)}</select></Field><Field label="DESTINATION SYSTEM"><input value={destinationSystem} onChange={(event) => setDestinationSystem(event.target.value)} className={inputClass} placeholder="e.g. HRIS integration" /></Field><Field label="TARGET START DATE"><input type="date" value={targetStartDate} onChange={(event) => setTargetStartDate(event.target.value)} className={inputClass} /></Field></div><FormActions saving={saving} onClose={onClose} label="Create handoff" /></form></Modal>;
}

export { TABS, COLLABORATION_GUARDRAILS, HIRING_DECISION_GUARDRAILS, OFFER_GUARDRAILS, formatDate };
