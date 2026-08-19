import React, { useMemo, useState } from "react";
import useSWR from "swr";
import {
  ArchiveRestore,
  BarChart3,
  Bell,
  CheckCircle2,
  Download,
  FileWarning,
  Loader2,
  LockKeyhole,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

const fetcher = (path) => api.get(path).then((response) => response.data);

export const CONTROL_PANELS = ["overview", "retention", "audit", "notifications", "administration"];
export const canManageEnterpriseControls = (user) => user?.role === "admin";

const statusTone = (status) => ({
  pending_review: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  on_hold: "border-sky-400/25 bg-sky-400/10 text-sky-200",
  approved_for_archive: "border-teal-400/25 bg-teal-400/10 text-teal-200",
  approved_for_erasure: "border-orange-400/25 bg-orange-400/10 text-orange-200",
  rejected: "border-slate-600 bg-slate-800 text-slate-300",
}[status] || "border-slate-700 bg-slate-900 text-slate-400");

function Metric({ label, value, detail, icon: Icon }) {
  return <div className="rounded-sm border border-slate-800 bg-slate-950/70 p-4 shadow-[0_12px_40px_rgba(2,6,23,.22)]">
    <div className="flex items-start justify-between"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">{label}</span><Icon className="h-4 w-4 text-violet-300" /></div>
    <div className="mt-3 font-display text-2xl font-black text-slate-100">{value ?? "—"}</div>
    <p className="mt-1 text-xs text-slate-500">{detail}</p>
  </div>;
}

export default function EnterpriseControls() {
  const { user } = useAuth();
  const isAdmin = canManageEnterpriseControls(user);
  const [activePanel, setActivePanel] = useState("overview");
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [executingCaseId, setExecutingCaseId] = useState("");
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [message, setMessage] = useState("");
  const [retentionForm, setRetentionForm] = useState({ subject_type: "candidate", subject_id: "", requested_action: "archive", reason: "", legal_hold: false });
  const { data: summary } = useSWR("/enterprise/operational-summary", fetcher);
  const { data: retentionCases = [], mutate: mutateRetention } = useSWR(isAdmin ? "/enterprise/retention-cases" : null, fetcher);
  const { data: exports = [], mutate: mutateExports } = useSWR(isAdmin ? "/enterprise/audit-exports" : null, fetcher);
  const { data: readiness } = useSWR(isAdmin ? "/enterprise/administration/readiness" : null, fetcher);
  const { data: notificationPreferences, mutate: mutateNotificationPreferences } = useSWR("/ats/notifications/preferences", fetcher);
  const pendingCases = useMemo(() => retentionCases.filter((item) => item.status === "pending_review").length, [retentionCases]);

  const requestExport = async () => {
    setExporting(true); setMessage("");
    try {
      const { data } = await api.post("/enterprise/audit-exports");
      const blob = new Blob([JSON.stringify({ manifest: data.manifest, events: data.events }, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `earos-audit-${data.manifest.audit_export_id}.json`;
      link.click(); URL.revokeObjectURL(link.href);
      await mutateExports();
      setMessage(`Export ${data.manifest.audit_export_id} created with ${data.manifest.event_count} events.`);
    } catch (error) { setMessage(error.response?.data?.detail || "Unable to create the audit export."); }
    finally { setExporting(false); }
  };

  const createCase = async (event) => {
    event.preventDefault(); setCreating(true); setMessage("");
    try {
      await api.post("/enterprise/retention-cases", retentionForm);
      setRetentionForm({ subject_type: "candidate", subject_id: "", requested_action: "archive", reason: "", legal_hold: false });
      await mutateRetention(); setMessage("Retention review case created. No data action has been performed.");
    } catch (error) { setMessage(error.response?.data?.detail || "Unable to create the retention review case."); }
    finally { setCreating(false); }
  };

  const decideCase = async (retentionCaseId, decision) => {
    try {
      await api.post(`/enterprise/retention-cases/${retentionCaseId}/decide`, { decision, note: "Reviewed in Enterprise Controls." });
      await mutateRetention(); setMessage(`Review recorded as ${decision.replaceAll("_", " ")}. No destructive action has been performed.`);
    } catch (error) { setMessage(error.response?.data?.detail || "Unable to record the review decision."); }
  };

  const executeApprovedCase = async (retentionCaseId) => {
    setExecutingCaseId(retentionCaseId); setMessage("");
    try {
      const { data } = await api.post(`/enterprise/retention-cases/${retentionCaseId}/execute`);
      await mutateRetention();
      setMessage(data.status === "awaiting_approval"
        ? "Retention execution entered the governance approval queue. No data action has been performed."
        : `Retention runtime completed with status ${data.status}. Review the immutable execution trace before closing the case.`);
    } catch (error) { setMessage(error.response?.data?.detail || "Unable to start the policy-gated retention action."); }
    finally { setExecutingCaseId(""); }
  };

  const saveNotificationPreferences = async (updates) => {
    if (!notificationPreferences) return;
    setSavingPreferences(true); setMessage("");
    try {
      await api.put("/ats/notifications/preferences", { in_app_enabled: notificationPreferences.in_app_enabled, email_enabled: notificationPreferences.email_enabled, interview_reminders: notificationPreferences.interview_reminders, approval_alerts: notificationPreferences.approval_alerts, candidate_activity_alerts: notificationPreferences.candidate_activity_alerts, ...updates });
      await mutateNotificationPreferences();
      setMessage("Your notification preferences were saved to the tenant-scoped audit trail.");
    } catch (error) { setMessage(error.response?.data?.detail || "Unable to save notification preferences."); }
    finally { setSavingPreferences(false); }
  };

  return <AppLayout>
    <div className="min-h-full bg-[radial-gradient(circle_at_88%_0%,rgba(45,212,191,.10),transparent_34%),radial-gradient(circle_at_2%_15%,rgba(124,58,237,.12),transparent_30%),#020617] px-5 py-6 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col gap-5 border-b border-slate-800/80 pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div><div className="mb-2 flex items-center gap-2 font-mono2 text-[10px] tracking-[.2em] text-teal-300"><ShieldCheck className="h-3.5 w-3.5" /> ENTERPRISE GOVERNANCE</div><h1 className="font-display text-3xl font-black tracking-tight text-white">Controls that make autonomy accountable.</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Review retention requests, route approved cases through policy-enforced execution, export immutable audit evidence, and check tenant administration readiness. EAROS never turns a review decision into an unobserved data action.</p></div>
          <div className="flex flex-wrap gap-2">{CONTROL_PANELS.map((panel) => <button key={panel} onClick={() => setActivePanel(panel)} className={`rounded-sm border px-3 py-2 font-mono2 text-[10px] tracking-wider transition ${activePanel === panel ? "border-violet-400/40 bg-violet-500/15 text-violet-200" : "border-slate-800 bg-slate-950 text-slate-500 hover:text-slate-200"}`}>{panel}</button>)}</div>
        </header>
        {!isAdmin && <div className="mb-5 flex gap-3 rounded-sm border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100"><LockKeyhole className="mt-0.5 h-4 w-4 shrink-0" />Control details and actions are restricted to workspace administrators. Your role can view the operational summary only.</div>}
        {message && <div className="mb-5 rounded-sm border border-teal-400/30 bg-teal-400/10 px-4 py-3 text-sm text-teal-100">{message}</div>}
        {activePanel === "overview" && <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="OPEN REQUISITIONS" value={summary?.requisitions?.open} detail={`${summary?.requisitions?.total ?? 0} records`} icon={UsersRound} /><Metric label="ACTIVE INTERVIEWS" value={summary?.interviews?.scheduled} detail={`${summary?.interviews?.total ?? 0} total sessions`} icon={BarChart3} /><Metric label="PENDING APPROVALS" value={summary?.governance?.pending_approvals} detail={`${summary?.governance?.executions ?? 0} governed runs`} icon={ShieldCheck} /><Metric label="RETENTION REVIEWS" value={isAdmin ? pendingCases : "Restricted"} detail="review before action" icon={ArchiveRestore} /></section>}
        {activePanel === "retention" && <section className="grid gap-5 xl:grid-cols-[.8fr_1.2fr]">{isAdmin ? <form onSubmit={createCase} className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><div className="flex items-center gap-2"><ArchiveRestore className="h-4 w-4 text-violet-300" /><h2 className="font-display font-bold text-slate-100">Create a review case</h2></div><p className="mt-2 text-sm leading-6 text-slate-500">This creates an auditable review request only. After an administrator review, the case must still pass the EAROS runtime policy and approval gate before any retention action can run.</p><div className="mt-5 grid gap-3"><select value={retentionForm.subject_type} onChange={(e) => setRetentionForm({ ...retentionForm, subject_type: e.target.value })} className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"><option value="candidate">Candidate</option><option value="application">Application</option></select><input required value={retentionForm.subject_id} onChange={(e) => setRetentionForm({ ...retentionForm, subject_id: e.target.value })} placeholder="Candidate or application ID" className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600" /><select value={retentionForm.requested_action} onChange={(e) => setRetentionForm({ ...retentionForm, requested_action: e.target.value })} className="rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"><option value="archive">Request archive review</option><option value="erase">Request erasure review</option></select><textarea required minLength={10} value={retentionForm.reason} onChange={(e) => setRetentionForm({ ...retentionForm, reason: e.target.value })} placeholder="Document the business or data-subject reason…" className="min-h-24 rounded-sm border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600" /><label className="flex items-center gap-2 text-sm text-slate-400"><input type="checkbox" checked={retentionForm.legal_hold} onChange={(e) => setRetentionForm({ ...retentionForm, legal_hold: e.target.checked })} /> Legal hold applies</label><button disabled={creating} className="inline-flex items-center justify-center gap-2 rounded-sm bg-violet-600 px-3 py-2.5 text-sm font-bold text-white transition hover:bg-violet-500 disabled:opacity-50"><FileWarning className="h-4 w-4" />{creating ? "Creating…" : "Create retention review"}</button></div></form> : <div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5 text-sm text-slate-500">Administrator access is required to create or decide retention reviews.</div>}<div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><h2 className="font-display font-bold text-slate-100">Review queue</h2><div className="mt-4 space-y-2">{retentionCases.length ? retentionCases.map((item) => <div key={item.retention_case_id} className="rounded-sm border border-slate-800 bg-slate-900/60 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><div className="text-sm font-semibold text-slate-200">{item.requested_action} · {item.subject_type}</div><div className="mt-0.5 font-mono2 text-[10px] text-slate-600">{item.retention_case_id} · {item.subject_id}</div></div><span className={`rounded-sm border px-2 py-1 font-mono2 text-[9px] tracking-wider ${statusTone(item.status)}`}>{item.status.replaceAll("_", " ")}</span></div><p className="mt-2 text-xs text-slate-500">{item.reason}</p>{item.status === "pending_review" && isAdmin && <div className="mt-3 flex gap-2"><button onClick={() => decideCase(item.retention_case_id, "on_hold")} className="rounded-sm border border-sky-400/30 px-2 py-1 text-xs text-sky-200">Place hold</button><button onClick={() => decideCase(item.retention_case_id, item.requested_action === "erase" ? "approved_for_erasure" : "approved_for_archive")} className="rounded-sm border border-teal-400/30 px-2 py-1 text-xs text-teal-200">Approve review</button></div>}{isAdmin && !item.legal_hold && ["approved_for_archive", "approved_for_erasure"].includes(item.status) && <div className="mt-3 rounded-sm border border-orange-400/20 bg-orange-400/5 p-2.5"><p className="text-xs leading-5 text-orange-100">This trigger creates a governed runtime execution. Organization policy may queue a second approval; no direct client-side data mutation occurs.</p><button disabled={executingCaseId === item.retention_case_id} onClick={() => executeApprovedCase(item.retention_case_id)} className="mt-2 inline-flex items-center gap-2 rounded-sm border border-orange-400/35 px-2.5 py-1.5 text-xs font-semibold text-orange-100 disabled:opacity-50"><ShieldCheck className="h-3.5 w-3.5" />{executingCaseId === item.retention_case_id ? "Starting policy gate…" : `Run ${item.requested_action} policy gate`}</button></div>}</div>) : <div className="rounded-sm border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-600">No retention review cases for this tenant.</div>}</div></div></section>}
        {activePanel === "audit" && <section className="grid gap-5 xl:grid-cols-[.8fr_1.2fr]"><div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><div className="flex items-center gap-2"><Download className="h-4 w-4 text-teal-300" /><h2 className="font-display font-bold text-slate-100">Audit evidence export</h2></div><p className="mt-2 text-sm leading-6 text-slate-500">Exports contain the tenant-scoped immutable event stream available at request time. The JSON file is delivered to the authenticated administrator’s device and its manifest is retained for accountability.</p><button disabled={!isAdmin || exporting} onClick={requestExport} className="mt-5 inline-flex items-center gap-2 rounded-sm border border-teal-400/35 bg-teal-400/10 px-3 py-2.5 text-sm font-bold text-teal-100 disabled:cursor-not-allowed disabled:opacity-40"><Download className="h-4 w-4" />{exporting ? "Preparing export…" : "Export audit evidence"}</button></div><div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><h2 className="font-display font-bold text-slate-100">Export manifests</h2><div className="mt-4 space-y-2">{exports.length ? exports.map((item) => <div key={item.audit_export_id} className="flex items-center justify-between rounded-sm border border-slate-800 bg-slate-900/60 px-3 py-2.5"><div><div className="font-mono2 text-[10px] text-slate-400">{item.audit_export_id}</div><div className="mt-1 text-xs text-slate-600">{item.event_count} events · {new Date(item.created_at).toLocaleString()}</div></div><span className="font-mono2 text-[9px] tracking-wider text-teal-300">{item.status}</span></div>) : <div className="rounded-sm border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-600">No exports requested for this tenant.</div>}</div></div></section>}
        {activePanel === "administration" && <section className="grid gap-5 lg:grid-cols-2"><div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><div className="flex items-center gap-2"><UsersRound className="h-4 w-4 text-violet-300" /><h2 className="font-display font-bold text-slate-100">Role administration</h2></div><p className="mt-2 text-sm text-slate-500">Roles are evaluated at the API boundary for tenant-scoped operations.</p><div className="mt-4 grid grid-cols-2 gap-2">{readiness?.roles?.map((role) => <div key={role.id} className="rounded-sm border border-slate-800 bg-slate-900/60 px-3 py-2"><div className="text-sm text-slate-200">{role.label}</div><div className="mt-1 font-mono2 text-[9px] text-slate-600">{role.id}</div></div>)}</div></div><div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><div className="flex items-center gap-2"><LockKeyhole className="h-4 w-4 text-teal-300" /><h2 className="font-display font-bold text-slate-100">SSO / SAML readiness</h2></div><div className="mt-4 rounded-sm border border-amber-400/25 bg-amber-400/10 p-3 font-mono2 text-[10px] tracking-wider text-amber-200">{readiness?.sso_saml?.status?.replaceAll("_", " ") || "ADMIN ACCESS REQUIRED"}</div><p className="mt-3 text-sm leading-6 text-slate-500">{readiness?.sso_saml?.secret_handling || "Identity-provider configuration is restricted to workspace administrators."}</p><div className="mt-4 flex flex-wrap gap-2">{readiness?.sso_saml?.required_configuration?.map((field) => <span key={field} className="rounded-sm border border-slate-800 px-2 py-1 font-mono2 text-[9px] text-slate-500">{field}</span>)}</div></div></section>}
      </div>
      {activePanel === "notifications" && <section className="mx-auto mt-5 grid max-w-7xl gap-5 lg:grid-cols-[1.2fr_.8fr]"><div className="rounded-sm border border-slate-800 bg-slate-950/75 p-5"><div className="flex items-center gap-2"><Bell className="h-4 w-4 text-teal-300" /><h2 className="font-display font-bold text-slate-100">Personal notification preferences</h2></div><p className="mt-2 text-sm leading-6 text-slate-500">These choices are scoped to your EAROS workspace identity and generate an immutable preference-change event. They do not configure a provider or transmit candidate data.</p><div className="mt-5 space-y-2">{[["in_app_enabled", "In-app alerts", "Surface approved work, queue changes, and system notices in EAROS."], ["email_enabled", "Email delivery preference", "Saved as a preference only; no email provider is configured."], ["interview_reminders", "Interview reminders", "Receive future reminder events when delivery is configured."], ["approval_alerts", "Approval alerts", "Notify when governed work enters or leaves a review gate."], ["candidate_activity_alerts", "Candidate activity alerts", "Notify when tracked candidate activity is recorded."]].map(([field, label, detail]) => <label key={field} className="flex items-center justify-between gap-5 rounded-sm border border-slate-800 bg-slate-900/60 px-3 py-3"><span><span className="block text-sm font-semibold text-slate-200">{label}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{detail}</span></span><input aria-label={label} type="checkbox" checked={Boolean(notificationPreferences?.[field])} disabled={!notificationPreferences || savingPreferences} onChange={(event) => saveNotificationPreferences({ [field]: event.target.checked })} className="h-4 w-4 shrink-0 accent-teal-400" /></label>)}</div></div><aside className="rounded-sm border border-amber-400/25 bg-amber-400/5 p-5"><div className="font-mono2 text-[10px] tracking-widest text-amber-200">DELIVERY STATUS</div><div className="mt-3 text-lg font-bold text-amber-100">{notificationPreferences?.provider_delivery_state || "loading"}</div><p className="mt-3 text-sm leading-6 text-amber-50/70">Email and outbound delivery are intentionally inactive until an administrator configures a compliant provider. EAROS retains your choices without claiming a notification has been sent.</p></aside></section>}
    </div>
  </AppLayout>;
}
