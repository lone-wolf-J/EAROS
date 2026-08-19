import { useMemo, useState } from "react";
import useSWR from "swr";
import { CheckCircle2, FileWarning, Loader2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

const fetcher = (path) => api.get(path).then((response) => response.data);

export const DATA_SUBJECT_GUARDRAILS = [
  "requests_are_tenant_scoped_and_human_reviewed",
  "access_requests_link_to_auditable_export_manifests",
  "erasure_requests_require_policy_gated_retention_execution",
  "no_direct_candidate_data_mutation_from_request_intake",
];

const statusTone = (status) => ({
  pending_review: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  on_hold: "border-sky-400/25 bg-sky-400/10 text-sky-200",
  approved: "border-teal-400/25 bg-teal-400/10 text-teal-200",
  fulfilled: "border-violet-400/25 bg-violet-400/10 text-violet-200",
  rejected: "border-slate-600 bg-slate-800 text-slate-300",
}[status] || "border-slate-700 bg-slate-900 text-slate-400");

export default function DataSubjectRequests({ isAdmin, onMessage }) {
  const [saving, setSaving] = useState(false);
  const [processingId, setProcessingId] = useState("");
  const [form, setForm] = useState({ candidate_id: "", request_type: "access", request_summary: "", intake_channel: "staff_recorded" });
  const { data: requests = [], mutate } = useSWR(isAdmin ? "/enterprise/data-subject-requests" : null, fetcher);
  const pendingCount = useMemo(() => requests.filter((request) => request.status === "pending_review").length, [requests]);

  const createRequest = async (event) => {
    event.preventDefault();
    setSaving(true); onMessage("");
    try {
      await api.post("/enterprise/data-subject-requests", form);
      setForm({ candidate_id: "", request_type: "access", request_summary: "", intake_channel: "staff_recorded" });
      await mutate();
      onMessage("Data-subject request recorded for review. No candidate data was changed.");
    } catch (error) {
      onMessage(error.response?.data?.detail || "Unable to record the data-subject request.");
    } finally { setSaving(false); }
  };

  const decideRequest = async (requestId, decision) => {
    setProcessingId(requestId); onMessage("");
    try {
      await api.post(`/enterprise/data-subject-requests/${requestId}/decide`, { decision, note: "Reviewed in Enterprise Controls." });
      await mutate();
      onMessage(decision === "approved" ? "Review recorded. The required fulfillment artifact was created where applicable." : `Request marked ${decision.replaceAll("_", " ")}.`);
    } catch (error) {
      onMessage(error.response?.data?.detail || "Unable to record the review decision.");
    } finally { setProcessingId(""); }
  };

  const fulfillRequest = async (requestId) => {
    setProcessingId(requestId); onMessage("");
    try {
      await api.post(`/enterprise/data-subject-requests/${requestId}/fulfill`);
      await mutate();
      onMessage("Fulfillment was recorded in the immutable candidate activity trail.");
    } catch (error) {
      onMessage(error.response?.data?.detail || "Unable to mark this request fulfilled.");
    } finally { setProcessingId(""); }
  };

  if (!isAdmin) return <section className="rounded-sm border border-slate-800 bg-slate-950/75 p-5 text-sm text-slate-500">Administrator access is required to review tenant data-subject requests.</section>;

  return <section className="grid gap-5 xl:grid-cols-[.78fr_1.22fr]">
    <form onSubmit={createRequest} className="rounded-sm border border-slate-800 bg-slate-950/75 p-5">
      <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-teal-300" /><h2 className="font-display font-bold text-slate-100">Data-subject request intake</h2></div>
      <p className="mt-2 text-sm leading-6 text-slate-500">Record a verified access, correction, or erasure request. EAROS creates a review record first; it does not expose, modify, or erase data from this form.</p>
      <div className="mt-5 grid gap-3">
        <input required value={form.candidate_id} onChange={(event) => setForm({ ...form, candidate_id: event.target.value })} placeholder="Candidate ID" className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600" />
        <select value={form.request_type} onChange={(event) => setForm({ ...form, request_type: event.target.value })} className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"><option value="access">Access request</option><option value="correction">Correction request</option><option value="erasure">Erasure request</option></select>
        <select value={form.intake_channel} onChange={(event) => setForm({ ...form, intake_channel: event.target.value })} className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"><option value="staff_recorded">Staff recorded</option><option value="candidate_portal">Candidate portal</option><option value="verified_email">Verified email</option></select>
        <textarea required minLength={10} value={form.request_summary} onChange={(event) => setForm({ ...form, request_summary: event.target.value })} placeholder="Verified request scope and identity-validation note…" className="min-h-28 rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600" />
        <button disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-sm bg-violet-600 px-3 py-2.5 text-sm font-bold text-white transition hover:bg-violet-500 disabled:opacity-50"><FileWarning className="h-4 w-4" />{saving ? "Recording…" : "Record for review"}</button>
      </div>
    </form>
    <div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-display font-bold text-slate-100">Governed request queue</h2><p className="mt-1 text-xs text-slate-500">{pendingCount} pending review{pendingCount === 1 ? "" : "s"} · tenant-scoped only</p></div><div className="font-mono2 text-[10px] tracking-widest text-slate-600">NO DIRECT DELETION</div></div>
      <div className="mt-4 space-y-2">{requests.length ? requests.map((request) => <article key={request.data_subject_request_id} className="rounded-sm border border-slate-800 bg-slate-900/60 p-3">
        <div className="flex flex-wrap items-start justify-between gap-2"><div><div className="text-sm font-semibold text-slate-200">{request.request_type} · candidate</div><div className="mt-0.5 font-mono2 text-[10px] text-slate-600">{request.data_subject_request_id} · {request.candidate_id}</div></div><span className={`rounded-sm border px-2 py-1 font-mono2 text-[9px] tracking-wider ${statusTone(request.status)}`}>{request.status.replaceAll("_", " ")}</span></div>
        <p className="mt-2 text-xs leading-5 text-slate-500">{request.request_summary}</p>
        {(request.audit_export_id || request.retention_case_id) && <div className="mt-2 rounded-sm border border-slate-800 bg-slate-950/60 px-2.5 py-2 font-mono2 text-[10px] text-slate-400">{request.audit_export_id ? `Access artifact: ${request.audit_export_id}` : `Erasure retention case: ${request.retention_case_id}`}</div>}
        {request.status === "pending_review" && <div className="mt-3 flex flex-wrap gap-2"><button disabled={processingId === request.data_subject_request_id} onClick={() => decideRequest(request.data_subject_request_id, "on_hold")} className="rounded-sm border border-sky-400/30 px-2 py-1 text-xs text-sky-200 disabled:opacity-50">Place hold</button><button disabled={processingId === request.data_subject_request_id} onClick={() => decideRequest(request.data_subject_request_id, "rejected")} className="rounded-sm border border-slate-600 px-2 py-1 text-xs text-slate-300 disabled:opacity-50">Reject</button><button disabled={processingId === request.data_subject_request_id} onClick={() => decideRequest(request.data_subject_request_id, "approved")} className="rounded-sm border border-teal-400/30 px-2 py-1 text-xs text-teal-200 disabled:opacity-50">Approve review</button></div>}
        {request.status === "approved" && <div className="mt-3 rounded-sm border border-teal-400/15 bg-teal-400/5 p-2.5"><p className="text-xs leading-5 text-teal-100">{request.request_type === "erasure" ? "Fulfillment stays blocked until the linked retention case completes its independent policy and approval path." : "Confirm fulfillment only after the linked access artifact or correction work has been independently completed."}</p><button disabled={processingId === request.data_subject_request_id} onClick={() => fulfillRequest(request.data_subject_request_id)} className="mt-2 inline-flex items-center gap-1.5 rounded-sm border border-teal-400/35 px-2.5 py-1.5 text-xs font-semibold text-teal-100 disabled:opacity-50">{processingId === request.data_subject_request_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}Record fulfillment</button></div>}
      </article>) : <div className="rounded-sm border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-600">No data-subject requests for this tenant.</div>}</div>
    </div>
  </section>;
}
