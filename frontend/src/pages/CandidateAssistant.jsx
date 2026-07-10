import React, { useState } from "react";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const FAQ = [
  {
    q: "How do I check my application status?",
    a: "Use the lookup on the right — your candidate_id is in your welcome email.",
  },
  {
    q: "When will I hear back?",
    a: "LevelShift averages 3–5 business days between stages. Time-sensitive updates come from your recruiter.",
  },
  {
    q: "Can I reschedule an interview?",
    a: "Yes — reply to your recruiter's latest email and propose two windows.",
  },
  {
    q: "How do offers work?",
    a: "Every offer at LevelShift requires human approval. AI recommends bands; hiring leaders decide.",
  },
];

export default function CandidateAssistant() {
  const [id, setId] = useState("cand_ai_staff_bang_00");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const lookup = async () => {
    setLoading(true);
    setErr(null);
    try {
      const { data } = await api.get(`/apps/candidate/${id}/status`);
      setStatus(data);
    } catch (e) {
      setErr("Candidate not found. Try `cand_ai_staff_bang_00`.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.candidateAssistantRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            CANDIDATE ASSISTANT
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Where you are in the process
          </h1>
          <div className="text-slate-500 text-sm">
            A candidate-safe view of stage, next step, and FAQs. No confidential
            data crosses this boundary.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-3">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              STATUS LOOKUP
            </div>
            <div className="flex gap-2">
              <input
                data-testid={EAROS.candidateIdInput}
                value={id}
                onChange={(e) => setId(e.target.value)}
                placeholder="candidate_id"
                className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[13px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500"
              />
              <button
                data-testid={EAROS.candidateLookupBtn}
                onClick={lookup}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2 disabled:opacity-50"
              >
                <Search className="w-3.5 h-3.5" strokeWidth={1.5} />
                {loading ? "…" : "LOOKUP"}
              </button>
            </div>
            {err && <div className="text-rose-400 text-[12px]">{err}</div>}
            {status && (
              <div className="border border-slate-800 bg-slate-950 rounded-sm p-4 space-y-2">
                <div className="font-display text-lg font-bold text-slate-100">
                  {status.full_name}
                </div>
                <div className="text-slate-400 text-[13px]">
                  {status.job_title} · {status.location}
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <span className="font-mono2 text-[10px] tracking-widest text-slate-500">
                    STAGE
                  </span>
                  <span className="px-1.5 py-0.5 rounded-sm border font-mono2 text-[11px] text-emerald-400 bg-emerald-500/10 border-emerald-500/30">
                    {status.stage}
                  </span>
                </div>
                <div className="mt-3">
                  <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
                    NEXT STEP
                  </div>
                  <div className="text-slate-200 text-[13px]">
                    {status.next_step}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-3">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              FAQ
            </div>
            <div className="space-y-3">
              {FAQ.map((f, i) => (
                <div key={i} className="border-b border-slate-800/60 pb-3 last:border-b-0">
                  <div className="text-slate-100 text-[13px] font-medium">
                    {f.q}
                  </div>
                  <div className="text-slate-400 text-[12px] mt-1">{f.a}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
