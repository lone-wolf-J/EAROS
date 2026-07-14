import React, { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import {
  CheckCircle2,
  Edit3,
  Mail,
  MessageCircle,
  Phone,
  Search,
  Send,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function OutreachStudio() {
  const { data: cands } = useSWR("/world/candidates", fetcher);
  const [candId, setCandId] = useState(null);
  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [q, setQ] = useState("");
  const [sentBanner, setSentBanner] = useState(null);

  useEffect(() => {
    if (cands && !candId) {
      setCandId(cands[0]?.candidate_id);
      setSelectedIds([cands[0]?.candidate_id]);
    }
  }, [cands, candId]);

  const filtered = useMemo(() => {
    if (!cands) return [];
    const query = q.trim().toLowerCase();
    return cands
      .filter((c) => {
        if (!query) return true;
        return (
          c.full_name?.toLowerCase().includes(query) ||
          c.current_title?.toLowerCase().includes(query) ||
          c.current_company?.toLowerCase().includes(query) ||
          c.location?.toLowerCase().includes(query)
        );
      })
      .slice(0, 80);
  }, [cands, q]);

  const toggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
    if (!candId) setCandId(id);
  };

  const draft = async () => {
    const target = candId || selectedIds[0];
    if (!target) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/outreach/pack/${target}`);
      setPack(data);
    } finally {
      setLoading(false);
    }
  };

  const sendCampaign = async (channelLabel) => {
    if (selectedIds.length === 0) return;
    // Simulate paced send
    setSentBanner({ channel: channelLabel, status: "sending", n: selectedIds.length });
    for (let i = 0; i < selectedIds.length; i++) {
      await new Promise((r) => setTimeout(r, 220));
    }
    setSentBanner({ channel: channelLabel, status: "sent", n: selectedIds.length });
    setTimeout(() => setSentBanner(null), 4500);
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

        {sentBanner && (
          <div
            data-testid="outreach-sent-banner"
            className={`px-4 py-3 border rounded-md flex items-center gap-2 font-mono2 text-[12px] ${
              sentBanner.status === "sending"
                ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-200"
                : "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
            }`}
          >
            {sentBanner.status === "sending" ? (
              <>
                <Send className="w-4 h-4 animate-pulse" strokeWidth={1.5} />
                Sending {sentBanner.channel} to {sentBanner.n} candidates…
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" strokeWidth={1.5} />
                {sentBanner.channel} sent to {sentBanner.n} candidates · tracked
                in Governance
              </>
            )}
          </div>
        )}

        {/* Candidate multi-select + generate */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div
            data-testid="outreach-candidate-list"
            className="lg:col-span-1 border border-slate-800 bg-slate-900 rounded-md overflow-hidden flex flex-col max-h-[500px]"
          >
            <div className="p-3 border-b border-slate-800/60 space-y-2">
              <div className="flex items-center gap-1.5 font-mono2 text-[10px] tracking-widest text-slate-500">
                <Search className="w-3 h-3" strokeWidth={1.5} />
                RECIPIENT LIST · {selectedIds.length} selected
              </div>
              <input
                data-testid="outreach-search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search candidates…"
                className="w-full px-2 py-1.5 bg-slate-950 border border-slate-800 rounded-sm text-[12px] text-slate-100 focus:outline-none focus:border-indigo-500/60"
              />
            </div>
            <div className="flex-1 overflow-y-auto divide-y divide-slate-800/40">
              {filtered.map((c) => {
                const active = selectedIds.includes(c.candidate_id);
                return (
                  <label
                    key={c.candidate_id}
                    data-testid={`outreach-recipient-${c.candidate_id}`}
                    className={`flex items-start gap-2 px-3 py-2 cursor-pointer hover:bg-slate-900/60 ${
                      active ? "bg-indigo-500/[0.05]" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleSelect(c.candidate_id)}
                      className="mt-1 accent-indigo-500"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-slate-100 text-[12.5px] truncate">
                        {c.full_name}
                      </div>
                      <div className="text-[10.5px] text-slate-500 truncate font-mono2">
                        {c.current_title} · {c.location}
                      </div>
                    </div>
                    <span className="font-mono2 text-[10px] text-slate-500 shrink-0">
                      {c.stage}
                    </span>
                  </label>
                );
              })}
              {filtered.length === 0 && (
                <div className="p-6 text-center text-slate-500 text-[12px]">
                  No candidates match &ldquo;{q}&rdquo;
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <select
                value={candId || ""}
                onChange={(e) => {
                  setCandId(e.target.value);
                  if (!selectedIds.includes(e.target.value)) {
                    setSelectedIds([...selectedIds, e.target.value]);
                  }
                }}
                className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100"
              >
                <option value="">— template based on —</option>
                {selectedIds
                  .map((id) => cands?.find((c) => c.candidate_id === id))
                  .filter(Boolean)
                  .map((c) => (
                    <option key={c.candidate_id} value={c.candidate_id}>
                      {c.full_name}
                    </option>
                  ))}
              </select>
              <button
                data-testid="outreach-generate-btn"
                onClick={draft}
                disabled={loading || selectedIds.length === 0}
                className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
              >
                <Send className="w-3.5 h-3.5" strokeWidth={1.5} />
                {loading ? "DRAFTING…" : "GENERATE PACK"}
              </button>
            </div>
            {!pack && !loading && (
              <div className="border border-dashed border-slate-800 rounded-md p-8 text-center text-slate-500 text-[13px]">
                Pick recipients on the left, then GENERATE PACK to draft
                per-tone email variants, LinkedIn, SMS, WhatsApp, and a voice
                script — each with modeled response probability.
              </div>
            )}
          </div>
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
                <EditableEmailVariant
                  key={v.tone}
                  variant={v}
                  recipientsN={selectedIds.length}
                  onSend={() => sendCampaign(`Email · ${v.tone}`)}
                />
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                ["LinkedIn InMail", pack.channels.linkedin, "indigo"],
                ["SMS", pack.channels.sms, "cyan"],
                ["WhatsApp", pack.channels.whatsapp, "emerald"],
                ["Voice Script", pack.channels.voice_script, "amber"],
              ].map(([label, ch]) => (
                <div key={label} className="border border-slate-800 bg-slate-900 rounded-md p-4 flex flex-col">
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
                  <div className="text-[12px] text-slate-300 whitespace-pre-wrap flex-1">
                    {ch.body}
                  </div>
                  <button
                    data-testid={`outreach-send-${label.toLowerCase().replace(/\s/g, "-")}`}
                    onClick={() => sendCampaign(label)}
                    disabled={selectedIds.length === 0}
                    className="mt-3 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-sm bg-indigo-500/15 hover:bg-indigo-500/30 border border-indigo-500/40 text-indigo-300 text-[11px] font-mono2 disabled:opacity-40"
                  >
                    <Send className="w-3 h-3" strokeWidth={1.5} />
                    SEND TO {selectedIds.length}
                  </button>
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


/* ============================================================
   TASK 7 — Editable email variant with per-tone send
   ============================================================ */

function EditableEmailVariant({ variant, recipientsN, onSend }) {
  const [subject, setSubject] = useState(variant.subject);
  const [body, setBody] = useState(variant.body);
  const [editing, setEditing] = useState(false);

  return (
    <div
      data-testid={`outreach-email-variant-${variant.tone}`}
      className="border border-slate-800 bg-slate-900 rounded-md p-4 flex flex-col"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-indigo-400" strokeWidth={1.5} />
          <div className="font-display font-bold text-slate-100">
            Email · <span className="text-indigo-300">{variant.tone}</span>
          </div>
        </div>
        <span className="font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
          {Math.round(variant.response_probability * 100)}% resp
        </span>
      </div>
      {editing ? (
        <>
          <input
            data-testid={`outreach-subject-${variant.tone}`}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="px-2 py-1.5 mb-2 bg-slate-950 border border-slate-800 rounded-sm text-[13px] text-slate-100 focus:outline-none focus:border-indigo-500/60"
          />
          <textarea
            data-testid={`outreach-body-${variant.tone}`}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={8}
            className="w-full flex-1 px-2 py-1.5 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500/60"
          />
        </>
      ) : (
        <>
          <div className="text-[13px] text-slate-100 font-medium mb-1">
            {subject}
          </div>
          <pre className="text-[12px] text-slate-300 whitespace-pre-wrap font-sans flex-1">
            {body}
          </pre>
        </>
      )}
      <div className="mt-3 flex items-center justify-between gap-2">
        <button
          data-testid={`outreach-edit-${variant.tone}`}
          onClick={() => setEditing((e) => !e)}
          className="flex items-center gap-1 font-mono2 text-[10px] text-slate-500 hover:text-slate-300"
        >
          <Edit3 className="w-3 h-3" strokeWidth={1.5} />
          {editing ? "done" : "edit"}
        </button>
        <button
          data-testid={`outreach-send-email-${variant.tone}`}
          onClick={onSend}
          disabled={recipientsN === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[11px] font-mono2 font-semibold disabled:opacity-40"
        >
          <Send className="w-3 h-3" strokeWidth={1.5} />
          SEND TO {recipientsN}
        </button>
      </div>
    </div>
  );
}

