import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { Mail, MessageCircle, Phone, Send } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function OutreachStudio() {
  const { data: cands } = useSWR("/world/candidates", fetcher);
  const [candId, setCandId] = useState(null);
  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (cands && !candId) setCandId(cands[0]?.candidate_id);
  }, [cands, candId]);

  const draft = async () => {
    if (!candId) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/outreach/pack/${candId}`);
      setPack(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.outreachRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <Send className="w-3.5 h-3.5" strokeWidth={1.5} />
            OUTREACH STUDIO
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Personalized outreach, every channel, A/B ready.
          </h1>
          <div className="text-slate-500 text-sm">
            Email (warm / direct / curiosity), LinkedIn InMail, SMS, WhatsApp,
            voice script + a 3-touch follow-up sequence — each with a modeled
            response probability.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={candId || ""}
            onChange={(e) => setCandId(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100"
          >
            {cands?.slice(0, 100).map((c) => (
              <option key={c.candidate_id} value={c.candidate_id}>
                {c.full_name} · {c.current_title} · {c.location}
              </option>
            ))}
          </select>
          <button
            onClick={draft}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
          >
            <Send className="w-3.5 h-3.5" strokeWidth={1.5} />
            {loading ? "DRAFTING…" : "GENERATE PACK"}
          </button>
        </div>

        {pack && (
          <>
            <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
              <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-2">
                EXPECTED RESPONSE PROBABILITY
              </div>
              <div className="font-display font-black text-3xl text-emerald-300">
                {Math.round(pack.expected_response_probability * 100)}%
              </div>
              <div className="mt-2 text-[12px] text-slate-400">
                Composite across ordered channels: {pack.recommended_send_order.join(" → ")}
              </div>
              <div className="mt-3 text-[12px]">
                <div className="font-mono2 text-slate-500 mb-1">PERSONALIZATION SIGNALS</div>
                <div className="text-slate-300 space-x-2">
                  {pack.personalization_signals.map((p, i) => (
                    <span key={i} className="inline-block px-1.5 py-0.5 rounded-sm border border-slate-800 text-[11px] font-mono2">
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {pack.channels.email_variants.map((v) => (
                <div key={v.tone} className="border border-slate-800 bg-slate-900 rounded-md p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-indigo-400" strokeWidth={1.5} />
                      <div className="font-display font-bold text-slate-100">
                        Email · <span className="text-indigo-300">{v.tone}</span>
                      </div>
                    </div>
                    <span className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                      {Math.round(v.response_probability * 100)}% resp
                    </span>
                  </div>
                  <div className="text-[13px] text-slate-100 font-medium mb-1">
                    {v.subject}
                  </div>
                  <pre className="text-[12px] text-slate-300 whitespace-pre-wrap font-sans">
                    {v.body}
                  </pre>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                ["LinkedIn InMail", pack.channels.linkedin, "indigo"],
                ["SMS", pack.channels.sms, "cyan"],
                ["WhatsApp", pack.channels.whatsapp, "emerald"],
                ["Voice Script", pack.channels.voice_script, "amber"],
              ].map(([label, ch, col]) => (
                <div key={label} className="border border-slate-800 bg-slate-900 rounded-md p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {label === "Voice Script"
                        ? <Phone className="w-4 h-4 text-amber-400" strokeWidth={1.5} />
                        : <MessageCircle className="w-4 h-4 text-slate-400" strokeWidth={1.5} />}
                      <div className="font-display font-bold text-slate-100">
                        {label}
                      </div>
                    </div>
                    <span className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                      {Math.round(ch.response_probability * 100)}%
                    </span>
                  </div>
                  {ch.subject && (
                    <div className="text-[13px] text-slate-100 font-medium mb-1">
                      {ch.subject}
                    </div>
                  )}
                  <div className="text-[12px] text-slate-300 whitespace-pre-wrap">
                    {ch.body}
                  </div>
                </div>
              ))}
            </div>

            <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
              <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
                FOLLOW-UP SEQUENCE
              </div>
              <ol className="space-y-2">
                {pack.follow_up_sequence.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 text-[13px]">
                    <span className="font-mono2 text-indigo-400 shrink-0 w-14">
                      Day {String(s.day).padStart(2, "0")}
                    </span>
                    <span className="font-mono2 text-slate-500 shrink-0 w-32">
                      via {s.channel}
                    </span>
                    <span className="text-slate-200">{s.hint}</span>
                  </li>
                ))}
              </ol>
            </div>

            <div className="border border-indigo-500/30 bg-indigo-500/5 rounded-md p-4">
              <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-2">
                AGENT REASONING
              </div>
              <ul className="space-y-1 text-[13px] text-slate-300 list-disc list-inside">
                {pack.reasoning.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
