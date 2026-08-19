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
  UsersRound,
} from "lucide-react";
import { api } from "@/lib/api";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((response) => response.data);

const TABS = [
  { key: "requisitions", label: "Requisitions", icon: BriefcaseBusiness },
  { key: "applications", label: "Applications", icon: ClipboardList },
  { key: "pools", label: "Talent pools", icon: FolderHeart },
  { key: "interviews", label: "Interviews", icon: CalendarDays },
  { key: "handoffs", label: "Onboarding", icon: Handshake },
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
  const { data: requisitions = [], mutate: mutateRequisitions } = useSWR("/ats/requisitions", fetcher);
  const { data: pipelines = [] } = useSWR("/ats/pipelines", fetcher);
  const { data: applications = [], mutate: mutateApplications } = useSWR("/ats/applications", fetcher);
  const { data: pools = [], mutate: mutatePools } = useSWR("/ats/talent-pools", fetcher);
  const { data: interviews = [], mutate: mutateInterviews } = useSWR("/ats/interviews", fetcher);
  const { data: candidates = [], mutate: mutateCandidates } = useSWR("/world/candidates", fetcher);
  const { data: offers = [] } = useSWR("/world/offers", fetcher);
  const { data: handoffs = [], mutate: mutateHandoffs } = useSWR("/ats/onboarding-handoffs", fetcher);

  const candidateById = useMemo(() => new Map(candidates.map((candidate) => [candidate.candidate_id, candidate])), [candidates]);
  const requisitionById = useMemo(() => new Map(requisitions.map((requisition) => [requisition.requisition_id, requisition])), [requisitions]);

  const refreshAll = () => Promise.all([mutateRequisitions(), mutateApplications(), mutatePools(), mutateInterviews(), mutateCandidates(), mutateHandoffs()]);
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
              <button onClick={() => setModal(tab === "requisitions" ? "requisition" : tab === "applications" ? "application" : tab === "pools" ? "pool" : tab === "interviews" ? "interview" : "handoff")} className="mb-2 inline-flex items-center gap-2 rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-xs font-bold text-white transition hover:brightness-110 active:scale-[0.98]">
                <Plus className="h-3.5 w-3.5" /> New {tab === "pools" ? "pool" : tab.slice(0, -1)}
              </button>
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
                <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">{interviews.map((interview) => <div key={interview.interview_id} className="flex flex-wrap items-center gap-4 bg-slate-950/40 px-4 py-4"><CalendarDays className="h-5 w-5 text-violet-300" /><div className="min-w-44 flex-1"><div className="font-semibold text-slate-100">{candidateById.get(interview.candidate_id)?.full_name || interview.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">{interview.interview_type} · {interview.duration_minutes} MIN · {interview.timezone}</div></div><div className="text-sm text-slate-300">{formatDate(interview.scheduled_at)}</div><Status value={interview.status} /></div>)}</div>
              ) : <EmptyState title="No interviews scheduled" detail="Structured interview records connect schedule metadata, interviewer assignments, scorecards, and feedback without exposing an AI agent to ungoverned execution." onCreate={() => setModal("interview")} />)}

              {tab === "handoffs" && (handoffs.length ? (
                <div className="divide-y divide-slate-800 overflow-hidden rounded-sm border border-slate-800">{handoffs.map((handoff) => <div key={handoff.onboarding_handoff_id} className="grid gap-3 bg-slate-950/40 px-4 py-4 transition hover:bg-slate-800/30 md:grid-cols-[1.6fr_1fr_auto] md:items-center"><div><div className="font-semibold text-slate-100">{candidateById.get(handoff.candidate_id)?.full_name || handoff.candidate_id}</div><div className="mt-1 font-mono2 text-[10px] text-slate-500">OFFER · {handoff.offer_id} · {handoff.destination_system || "Destination pending"}</div></div><div className="text-xs text-slate-400">START · {handoff.target_start_date || "Not scheduled"}<div className="mt-1 font-mono2 text-[10px] text-slate-600">{handoff.checklist?.length || 0} routing items</div></div><Status value={handoff.status} /></div>)}</div>
              ) : <EmptyState title="Handoff accepted hires with context, not secrets" detail="Create a minimal routing record from an accepted offer. Payroll, identity-provider credentials, and background-check files remain in the downstream onboarding system." onCreate={() => setModal("handoff")} />)}
            </div>
          </section>
        </div>

        {modal === "requisition" && <RequisitionForm pipelines={pipelines} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/requisitions", body, mutateRequisitions)} />}
        {modal === "candidate" && <CandidateForm saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/candidates", body, mutateCandidates)} />}
        {modal === "application" && <ApplicationForm candidates={candidates} requisitions={requisitions} pipelines={pipelines} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/applications", body, mutateApplications)} onCreateCandidate={() => setModal("candidate")} />}
        {modal === "pool" && <PoolForm saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/talent-pools", body, mutatePools)} />}
        {modal === "interview" && <InterviewForm applications={applications} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/interviews", body, mutateInterviews)} />}
        {modal === "handoff" && <HandoffForm offers={offers} candidates={candidateById} saving={saving} onClose={() => setModal(null)} onSubmit={(body) => create("/ats/onboarding-handoffs", body, mutateHandoffs)} />}
      </div>
    </AppLayout>
  );
}

function FormActions({ saving, onClose, label }) { return <div className="flex justify-end gap-2 border-t border-slate-800 px-5 py-4"><button type="button" onClick={onClose} className="rounded-sm px-3 py-2 text-sm text-slate-400 hover:bg-slate-800">Cancel</button><button disabled={saving} className="rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-sm font-bold text-white disabled:cursor-wait disabled:opacity-60">{saving ? "Saving…" : label}</button></div>; }

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

function HandoffForm({ offers, candidates, saving, onClose, onSubmit }) {
  const [offerId, setOfferId] = useState(""); const [destinationSystem, setDestinationSystem] = useState(""); const [targetStartDate, setTargetStartDate] = useState("");
  const acceptedOffers = offers.filter((offer) => offer.status === "accepted");
  return <Modal title="Create onboarding handoff" onClose={onClose}><form onSubmit={(event) => { event.preventDefault(); const offer = acceptedOffers.find((item) => item.offer_id === offerId); if (!offer) return; onSubmit({ offer_id: offer.offer_id, candidate_id: offer.candidate_id, job_id: offer.job_id, destination_system: destinationSystem || null, target_start_date: targetStartDate || null, checklist: [] }); }}><div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-teal-500/20 bg-teal-500/5 px-3 py-2 text-xs leading-5 text-teal-100">Only accepted offers can transfer. This record routes work; it deliberately never stores payroll, credentials, or background-check documents.</div><Field label="ACCEPTED OFFER"><select required value={offerId} onChange={(event) => setOfferId(event.target.value)} className={inputClass}><option value="">Select an accepted offer</option>{acceptedOffers.map((offer) => <option key={offer.offer_id} value={offer.offer_id}>{candidates.get(offer.candidate_id)?.full_name || offer.candidate_id} · {offer.offer_id}</option>)}</select></Field><Field label="DESTINATION SYSTEM"><input value={destinationSystem} onChange={(event) => setDestinationSystem(event.target.value)} className={inputClass} placeholder="e.g. HRIS integration" /></Field><Field label="TARGET START DATE"><input type="date" value={targetStartDate} onChange={(event) => setTargetStartDate(event.target.value)} className={inputClass} /></Field></div><FormActions saving={saving} onClose={onClose} label="Create handoff" /></form></Modal>;
}

export { TABS, formatDate };
