import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { ClipboardCheck } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function Screening() {
  const { data: cands } = useSWR("/world/candidates", fetcher);
  const [candId, setCandId] = useState(null);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (cands && !candId) setCandId(cands[0]?.candidate_id);
  }, [cands, candId]);

  const run = async () => {
    if (!candId) return;
    setLoading(true);
    try {
      const { data } = await api.post("/screening/rubric", {
        candidate_id: candId, notes,
      });
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.screeningRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <ClipboardCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
            SCREENING · 8-DIMENSION RUBRIC
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Structured screen. Explainable score.
          </h1>
          <div className="text-slate-500 text-sm">
            Every candidate is scored on Technical, Communication, Leadership,
            Culture, Problem Solving, Domain, Motivation, and Availability —
            weighted, then composited.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4">
          <div className="border border-slate-800 bg-slate-900 rounded-md p-4 space-y-2">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              INPUTS
            </div>
            <select
              value={candId || ""}
              onChange={(e) => setCandId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100"
            >
              {cands?.slice(0, 100).map((c) => (
                <option key={c.candidate_id} value={c.candidate_id}>
                  {c.full_name} · {c.current_company}
                </option>
              ))}
            </select>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={6}
              placeholder="Interviewer notes (optional)…"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] text-slate-100"
            />
            <button
              onClick={run}
              disabled={loading}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-40"
            >
              {loading ? "SCORING…" : "RUN RUBRIC"}
            </button>
          </div>

          <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
            {!result && (
              <div className="text-slate-500 text-[12px] text-center py-8">
                Run the rubric to see per-dimension scores + recommendation.
              </div>
            )}
            {result && (
              <>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="font-display font-bold text-lg text-slate-100">
                      {result.candidate_name}
                    </div>
                    <div className="font-mono2 text-[10px] text-slate-500">
                      recommendation · {result.recommendation.replace(/_/g, " ")}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-display font-black text-4xl leading-none text-emerald-300">
                      {Math.round(result.composite_score * 100)}
                    </div>
                    <div className={`mt-1 inline-block px-2 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                      result.band === "STRONG"
                        ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                        : result.band === "GOOD"
                          ? "text-cyan-400 border-cyan-500/30 bg-cyan-500/10"
                          : result.band === "MIXED"
                            ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                            : "text-rose-400 border-rose-500/30 bg-rose-500/10"
                    }`}>
                      {result.band} · confidence {Math.round(result.confidence * 100)}%
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {result.rubric.map((d) => (
                    <div key={d.dimension} className="border border-slate-800 rounded-sm p-2 bg-slate-950">
                      <div className="flex items-center gap-3">
                        <div className="w-32 text-[12px] text-slate-100">{d.dimension}</div>
                        <div className="flex-1 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
                          <div className="h-full bg-emerald-400"
                               style={{ width: `${d.score * 100}%` }} />
                        </div>
                        <div className="w-14 text-right font-mono2 text-[11px] text-slate-200">
                          {Math.round(d.score * 100)}
                        </div>
                        <div className="w-14 text-right font-mono2 text-[10px] text-slate-500">
                          wt {Math.round(d.weight * 100)}%
                        </div>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-400">{d.notes}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 text-[13px] text-slate-300 border-t border-slate-800/60 pt-3">
                  {result.summary}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
