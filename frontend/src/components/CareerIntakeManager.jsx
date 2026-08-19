import { useState } from "react";
import { ArrowRight, UsersRound } from "lucide-react";

export const CAREER_INTAKE_GUARDRAILS = [
  "career_site_link_requires_published_and_enabled_requisition",
  "referral_submission_requires_explicit_intake_enablement",
  "referral_source_and_referrer_are_recorded_server_side",
  "intake_controls_do_not_trigger_outbound_automation",
];

const inputClass = "w-full rounded-sm border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-700 focus:border-indigo-500";

export function CareerIntakeManager({ requisitions, selectedRequisitionId, onRecordReferral }) {
  const requisition = requisitions.find((item) => item.requisition_id === selectedRequisitionId);
  if (!requisition) return null;
  const careerSitePath = `/careers?org=${encodeURIComponent(requisition.organization_id)}`;
  const careerSiteReady = requisition.career_site_enabled && requisition.internal_publication_status === "published";
  return (
    <section className="rounded-sm border border-teal-400/20 bg-teal-400/5 p-4" data-testid="career-intake-manager">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-mono2 text-[10px] tracking-widest text-teal-200">CAREER & REFERRAL INTAKE</div>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">Public applications and employee referrals create canonical EAROS candidates and applications with source attribution. Neither action initiates outreach.</p>
        </div>
        <UsersRound className="h-5 w-5 text-teal-200/50" />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-sm border border-slate-800 bg-slate-950/50 p-3">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500">CAREER SITE</div>
          <p className="mt-2 text-xs leading-5 text-slate-400">{careerSiteReady ? "This requisition is available for consented public applications." : "Publish the internal career-site state and enable intake in Publication Control before exposing an application link."}</p>
          {careerSiteReady && <a href={careerSitePath} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 rounded-sm border border-teal-400/35 px-2.5 py-1.5 text-xs font-semibold text-teal-100 transition hover:bg-teal-400/10">Open public application form <ArrowRight className="h-3.5 w-3.5" /></a>}
        </div>
        <div className="rounded-sm border border-slate-800 bg-slate-950/50 p-3">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500">EMPLOYEE REFERRALS</div>
          <p className="mt-2 text-xs leading-5 text-slate-400">{requisition.referral_intake_enabled ? "Record a referral from a verified organization member. Duplicate applications remain blocked." : "Enable employee referrals in Publication Control before recording referral intake."}</p>
          <button type="button" disabled={!requisition.referral_intake_enabled} onClick={onRecordReferral} className="mt-3 rounded-sm border border-violet-400/35 px-2.5 py-1.5 text-xs font-semibold text-violet-100 transition hover:bg-violet-400/10 disabled:cursor-not-allowed disabled:opacity-40">Record employee referral</button>
        </div>
      </div>
    </section>
  );
}

export function ReferralIntakeForm({ requisition, saving, onClose, onSubmit }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [referrerUserId, setReferrerUserId] = useState("");
  const [note, setNote] = useState("");
  if (!requisition) return null;
  const submit = (event) => {
    event.preventDefault();
    onSubmit({
      full_name: fullName,
      email: email || null,
      phone: phone || null,
      current_title: currentTitle,
      location,
      skills: skills.split(",").map((skill) => skill.trim()).filter(Boolean),
      referrer_user_id: referrerUserId,
      note: note || null,
    });
  };
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-slate-950/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Record employee referral">
      <div className="w-full max-w-lg rounded-md border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4"><div><div className="font-mono2 text-[10px] tracking-[0.18em] text-teal-300">EAROS / REFERRAL INTAKE</div><h2 className="font-display text-xl font-black text-slate-100">Record employee referral</h2></div><button type="button" onClick={onClose} className="rounded-sm px-2 py-1 text-sm text-slate-400 hover:bg-slate-800 hover:text-white">Close</button></div>
        <form onSubmit={submit}>
          <div className="grid gap-4 px-5 py-5"><div className="rounded-sm border border-violet-400/25 bg-violet-400/5 px-3 py-2 text-xs leading-5 text-violet-100">This records a trusted referral against <strong>{requisition.title}</strong>. EAROS validates the referring user in this organization and does not send outreach automatically.</div><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">CANDIDATE FULL NAME</span><input required value={fullName} onChange={(event) => setFullName(event.target.value)} className={inputClass} /></label><div className="grid grid-cols-2 gap-3"><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">EMAIL</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">PHONE</span><input value={phone} onChange={(event) => setPhone(event.target.value)} className={inputClass} /></label></div><div className="grid grid-cols-2 gap-3"><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">CURRENT TITLE</span><input value={currentTitle} onChange={(event) => setCurrentTitle(event.target.value)} className={inputClass} /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">LOCATION</span><input value={location} onChange={(event) => setLocation(event.target.value)} className={inputClass} /></label></div><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">SKILLS</span><input value={skills} onChange={(event) => setSkills(event.target.value)} className={inputClass} placeholder="Comma-separated skills" /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">REFERRING USER ID</span><input required value={referrerUserId} onChange={(event) => setReferrerUserId(event.target.value)} className={inputClass} placeholder="Verified organization member ID" /></label><label className="block space-y-1.5"><span className="font-mono2 text-[10px] tracking-widest text-slate-500">REFERRAL NOTE</span><textarea value={note} onChange={(event) => setNote(event.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="Optional role-relevant context" /></label></div>
          <div className="flex justify-end gap-2 border-t border-slate-800 px-5 py-4"><button type="button" onClick={onClose} className="rounded-sm px-3 py-2 text-sm text-slate-400 hover:bg-slate-800">Cancel</button><button disabled={saving} className="rounded-sm bg-gradient-to-r from-violet-600 to-teal-500 px-3 py-2 text-sm font-bold text-white disabled:cursor-wait disabled:opacity-60">{saving ? "Saving…" : "Record referral"}</button></div>
        </form>
      </div>
    </div>
  );
}
