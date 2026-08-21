import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { BriefcaseBusiness, CheckCircle2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

export const CAREER_SITE_GUARDRAILS = [
  "only_enabled_open_requisitions_are_listed",
  "recruiting_consent_is_required_before_submission",
  "candidate_and_application_records_use_canonical_ats_models",
  "requisition_configured_questions_are_validated_and_stored_canonically",
  "candidate_withdrawal_requires_a_one_time_reference_and_preserves_application_provenance",
  "submission_never_triggers_outbound_automation",
];

const inputClass = "w-full rounded-sm border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-teal-400";

export default function CareerSite() {
  const [searchParams] = useSearchParams();
  const [organizationId, setOrganizationId] = useState(searchParams.get("org") || "");
  const [requisitions, setRequisitions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(null);
  const [withdrawal, setWithdrawal] = useState({ applicationId: "", withdrawalReference: "", reason: "" });
  const [withdrawalError, setWithdrawalError] = useState("");
  const [withdrawalResult, setWithdrawalResult] = useState(null);
  const [withdrawing, setWithdrawing] = useState(false);
  const [answers, setAnswers] = useState({});
  const [form, setForm] = useState({
    requisitionId: "",
    fullName: "",
    email: "",
    phone: "",
    location: "",
    currentTitle: "",
    skills: "",
    consent: false,
  });

  useEffect(() => {
    let active = true;
    if (!organizationId.trim()) {
      setRequisitions([]);
      return undefined;
    }
    setLoading(true);
    setLoadError("");
    api.get(`/public/ats/career-sites/${encodeURIComponent(organizationId.trim())}/requisitions`)
      .then(({ data }) => {
        if (!active) return;
        setRequisitions(data || []);
        setForm((previous) => ({
          ...previous,
          requisitionId: data?.some((requisition) => requisition.requisition_id === previous.requisitionId)
            ? previous.requisitionId
            : data?.[0]?.requisition_id || "",
        }));
      })
      .catch(() => active && setLoadError("No published careers are available for this organization identifier."))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [organizationId]);

  const update = (field, value) => setForm((previous) => ({ ...previous, [field]: value }));
  const selectedRequisition = requisitions.find((requisition) => requisition.requisition_id === form.requisitionId);
  const updateAnswer = (questionId, value) => setAnswers((previous) => ({ ...previous, [questionId]: value }));

  const selectRequisition = (requisitionId) => {
    update("requisitionId", requisitionId);
    const requisition = requisitions.find((item) => item.requisition_id === requisitionId);
    setAnswers(Object.fromEntries((requisition?.application_questions || []).map((question) => [
      question.question_id, question.type === "boolean" ? false : question.type === "multi_select" ? [] : "",
    ])));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitError("");
    setSubmitted(null);
    if (!form.requisitionId) return setSubmitError("Choose an available role before submitting your application.");
    if (!form.consent) return setSubmitError("Please provide recruiting consent before submitting your application.");
    setSubmitting(true);
    try {
      const { data } = await api.post(`/public/ats/requisitions/${form.requisitionId}/applications`, {
        organization_id: organizationId.trim(),
        full_name: form.fullName,
        email: form.email || null,
        phone: form.phone || null,
        location: form.location,
        current_title: form.currentTitle,
        skills: form.skills.split(",").map((skill) => skill.trim()).filter(Boolean),
        consent_to_recruit: true,
        application_answers: (selectedRequisition?.application_questions || []).map((question) => ({
          question_id: question.question_id,
          value: answers[question.question_id],
        })),
      });
      setSubmitted(data);
      setWithdrawal((previous) => ({ ...previous, applicationId: data.application_id, withdrawalReference: data.withdrawal_reference || "" }));
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setSubmitError(typeof detail === "string" ? detail : "Your application could not be recorded. Please verify the role is still open and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const withdraw = async (event) => {
    event.preventDefault();
    setWithdrawalError("");
    setWithdrawalResult(null);
    if (!withdrawal.applicationId || !withdrawal.withdrawalReference) {
      setWithdrawalError("Enter the application reference and the one-time withdrawal reference.");
      return;
    }
    setWithdrawing(true);
    try {
      const { data } = await api.post(`/public/ats/applications/${encodeURIComponent(withdrawal.applicationId)}/withdraw`, {
        withdrawal_reference: withdrawal.withdrawalReference,
        reason: withdrawal.reason || null,
      });
      setWithdrawalResult(data);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setWithdrawalError(typeof detail === "string" ? detail : "This application could not be withdrawn. Verify both references and try again.");
    } finally {
      setWithdrawing(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-8 lg:px-16">
      <section className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-md border border-teal-500/20 bg-gradient-to-br from-violet-950 via-slate-900 to-teal-950 p-7 shadow-2xl shadow-teal-950/20 sm:p-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-teal-300/25 bg-teal-300/10 px-3 py-1 font-mono2 text-[10px] tracking-[0.18em] text-teal-200">
            <ShieldCheck className="h-3.5 w-3.5" /> EAROS CAREERS
          </div>
          <h1 className="mt-6 font-display text-4xl font-black leading-tight text-white sm:text-5xl">Find your next meaningful role.</h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-300">Apply directly to recruiter-enabled opportunities. Your application enters a governed hiring workflow with a clear consent record and no automated outreach.</p>
          <div className="mt-8 space-y-3 rounded-md border border-white/10 bg-slate-950/45 p-4 text-sm text-slate-300">
            <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-300" /> Only open positions deliberately enabled by the hiring team appear here.</div>
            <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-300" /> Recruiting consent is captured before any candidate record is created.</div>
            <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-300" /> Submission confirms receipt only; EAROS does not send messages from this form.</div>
          </div>
        </div>

        <section className="rounded-md border border-slate-800 bg-slate-900 p-6 shadow-xl shadow-black/20 sm:p-8" aria-labelledby="application-form-title">
          <div className="flex items-center gap-3">
            <div className="rounded-sm border border-violet-400/25 bg-violet-400/10 p-2 text-violet-200"><BriefcaseBusiness className="h-5 w-5" /></div>
            <div><div className="font-mono2 text-[10px] tracking-[0.18em] text-teal-300">CANDIDATE INTAKE</div><h2 id="application-form-title" className="font-display text-2xl font-black">Application form</h2></div>
          </div>
          {submitted ? (
            <div className="mt-7 rounded-md border border-emerald-400/25 bg-emerald-400/10 p-5 text-emerald-100">
              <CheckCircle2 className="mb-2 h-6 w-6" />
              <div className="font-display text-xl font-black">Application recorded</div>
              <p className="mt-1 text-sm text-emerald-100/80">Reference: <span className="font-mono2">{submitted.application_id}</span>. A hiring team member will review your application through their governed workflow.</p>
              {submitted.withdrawal_reference && <div data-testid="career-site-withdrawal-reference" className="mt-4 rounded-sm border border-emerald-200/20 bg-slate-950/30 p-3 text-sm text-emerald-50"><strong>Save this private withdrawal reference now:</strong> <span className="mt-1 block break-all font-mono2 text-xs">{submitted.withdrawal_reference}</span><span className="mt-2 block text-emerald-100/80">EAROS does not send this reference by email. It is required only if you later choose to withdraw this application.</span></div>}
            </div>
          ) : (
            <form className="mt-7 space-y-4" onSubmit={submit}>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">ORGANIZATION IDENTIFIER</span><input className={inputClass} value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} placeholder="Organization identifier" required /></label>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">OPEN ROLE</span><select className={inputClass} value={form.requisitionId} onChange={(event) => selectRequisition(event.target.value)} disabled={loading || !requisitions.length} required><option value="">{loading ? "Loading open roles…" : "Choose a role"}</option>{requisitions.map((requisition) => <option key={requisition.requisition_id} value={requisition.requisition_id}>{requisition.title}{requisition.location ? ` · ${requisition.location}` : ""}</option>)}</select></label>
              {loadError && <p className="rounded-sm border border-rose-500/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{loadError}</p>}
              <div className="grid gap-4 sm:grid-cols-2"><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">FULL NAME</span><input className={inputClass} value={form.fullName} onChange={(event) => update("fullName", event.target.value)} required /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">EMAIL</span><input className={inputClass} type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label></div>
              <div className="grid gap-4 sm:grid-cols-2"><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">PHONE</span><input className={inputClass} value={form.phone} onChange={(event) => update("phone", event.target.value)} /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">LOCATION</span><input className={inputClass} value={form.location} onChange={(event) => update("location", event.target.value)} /></label></div>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">CURRENT TITLE</span><input className={inputClass} value={form.currentTitle} onChange={(event) => update("currentTitle", event.target.value)} /></label>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">SKILLS</span><input className={inputClass} value={form.skills} onChange={(event) => update("skills", event.target.value)} placeholder="Comma-separated skills" /></label>
              {!!selectedRequisition?.application_questions?.length && <fieldset className="space-y-4 rounded-sm border border-teal-400/20 bg-teal-400/5 p-4"><legend className="px-1 font-mono2 text-[10px] tracking-widest text-teal-200">ROLE-SPECIFIC QUESTIONS</legend>{selectedRequisition.application_questions.map((question) => <label key={question.question_id} className="block space-y-1.5"><span className="text-sm font-medium text-slate-200">{question.label}{question.required ? <span className="ml-1 text-teal-300">*</span> : null}</span>{question.type === "textarea" ? <textarea className={inputClass} value={answers[question.question_id] || ""} onChange={(event) => updateAnswer(question.question_id, event.target.value)} required={question.required} /> : question.type === "boolean" ? <span className="flex gap-3 rounded-sm border border-slate-700 bg-slate-950/60 p-3 text-sm text-slate-300"><input className="mt-0.5 h-4 w-4 accent-teal-400" type="checkbox" checked={Boolean(answers[question.question_id])} onChange={(event) => updateAnswer(question.question_id, event.target.checked)} required={question.required} />Confirm</span> : question.type === "single_select" ? <select className={inputClass} value={answers[question.question_id] || ""} onChange={(event) => updateAnswer(question.question_id, event.target.value)} required={question.required}><option value="">Choose an option</option>{question.options.map((option) => <option key={option} value={option}>{option}</option>)}</select> : question.type === "multi_select" ? <select className={inputClass} multiple value={answers[question.question_id] || []} onChange={(event) => updateAnswer(question.question_id, Array.from(event.target.selectedOptions, (option) => option.value))} required={question.required}>{question.options.map((option) => <option key={option} value={option}>{option}</option>)}</select> : <input className={inputClass} value={answers[question.question_id] || ""} onChange={(event) => updateAnswer(question.question_id, event.target.value)} required={question.required} />}</label>)}</fieldset>}
              <label className="flex gap-3 rounded-sm border border-slate-700 bg-slate-950/60 p-3 text-sm text-slate-300"><input className="mt-1 h-4 w-4 accent-teal-400" type="checkbox" checked={form.consent} onChange={(event) => update("consent", event.target.checked)} required /><span>I consent to the organization processing this application for recruiting. I understand this form records my application and does not send automated messages.</span></label>
              {submitError && <p className="rounded-sm border border-rose-500/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{submitError}</p>}
              <button type="submit" disabled={submitting || loading || !requisitions.length} className="w-full rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-4 py-3 font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? "Recording application…" : "Submit application"}</button>
            </form>
          )}
          <section className="mt-7 border-t border-slate-800 pt-6" aria-labelledby="withdraw-application-title">
            <div className="font-mono2 text-[10px] tracking-[0.18em] text-slate-400">CANDIDATE SELF-SERVICE</div>
            <h3 id="withdraw-application-title" className="mt-1 font-display text-lg font-black text-slate-100">Withdraw an application</h3>
            <p className="mt-1 text-sm leading-6 text-slate-400">Withdrawal ends only the active application. It does not erase personal data, revoke recruiting consent, or send a message. Those actions remain separately governed.</p>
            {withdrawalResult ? <p data-testid="career-site-withdrawal-confirmation" className="mt-3 rounded-sm border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-100">Application <span className="font-mono2">{withdrawalResult.application_id}</span> was withdrawn.</p> : <form className="mt-4 space-y-3" onSubmit={withdraw}>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">APPLICATION REFERENCE</span><input className={inputClass} value={withdrawal.applicationId} onChange={(event) => setWithdrawal((previous) => ({ ...previous, applicationId: event.target.value }))} required /></label>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">PRIVATE WITHDRAWAL REFERENCE</span><input className={inputClass} type="password" autoComplete="off" value={withdrawal.withdrawalReference} onChange={(event) => setWithdrawal((previous) => ({ ...previous, withdrawalReference: event.target.value }))} required /></label>
              <label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-400">OPTIONAL NOTE</span><textarea className={inputClass} value={withdrawal.reason} onChange={(event) => setWithdrawal((previous) => ({ ...previous, reason: event.target.value }))} /></label>
              {withdrawalError && <p className="rounded-sm border border-rose-500/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{withdrawalError}</p>}
              <button type="submit" disabled={withdrawing} className="rounded-sm border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-teal-400 hover:text-teal-200 disabled:cursor-not-allowed disabled:opacity-50">{withdrawing ? "Withdrawing application…" : "Withdraw application"}</button>
            </form>}
          </section>
        </section>
      </section>
    </main>
  );
}
