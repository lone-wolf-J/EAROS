import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { Mic, Play, StopCircle } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function VoiceInterview() {
  const { data: cands } = useSWR("/world/candidates", fetcher);
  const [candId, setCandId] = useState(null);
  const [plan, setPlan] = useState(null);
  const [turns, setTurns] = useState([]);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (cands && !candId) setCandId(cands[0]?.candidate_id);
  }, [cands, candId]);

  const start = async () => {
    if (!candId) return;
    setSummary(null);
    setTurns([]);
    const { data } = await api.get(`/voice/plan/${candId}`);
    setPlan(data);
    setRunning(true);
    // step through first turn immediately
    await nextTurn(0);
  };

  const nextTurn = async (idx) => {
    if (!candId) return;
    const { data } = await api.get(`/voice/turn/${candId}/${idx}`);
    if (data.done) {
      setRunning(false);
      return;
    }
    setTurns((t) => [...t, data]);
  };

  const advance = async () => {
    if (!plan) return;
    const nextIdx = turns.length;
    if (nextIdx >= plan.plan.length) {
      setRunning(false);
      return;
    }
    await nextTurn(nextIdx);
  };

  const summarize = async () => {
    const { data } = await api.post("/voice/summarize", {
      candidate_id: candId, turns,
    });
    setSummary(data);
    setRunning(false);
  };

  const KIND_TINT = {
    opener: "text-slate-400 border-slate-500/30 bg-slate-500/10",
    technical: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10",
    behavioral: "text-violet-400 border-violet-500/30 bg-violet-500/10",
    domain: "text-amber-400 border-amber-500/30 bg-amber-500/10",
    closing: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.voiceRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <Mic className="w-3.5 h-3.5" strokeWidth={1.5} />
            VOICE INTERVIEW · INTERACTIVE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Live transcription. Structured evaluation.
          </h1>
          <div className="text-slate-500 text-sm">
            Simulated realtime interview with STAR extraction, sentiment, and
            per-dimension signal — all human-reviewable before advancing.
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
                {c.full_name} · {c.current_title}
              </option>
            ))}
          </select>
          {!running && !summary && (
            <button
              data-testid={EAROS.voiceStartBtn}
              onClick={start}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold"
            >
              <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
              START INTERVIEW
            </button>
          )}
          {running && plan && turns.length < plan.plan.length && (
            <button
              data-testid={EAROS.voiceNextBtn}
              onClick={advance}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-[12px] font-mono2"
            >
              NEXT QUESTION →
            </button>
          )}
          {running && turns.length > 0 && (
            <button
              data-testid={EAROS.voiceSummarizeBtn}
              onClick={summarize}
              className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2"
            >
              <StopCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
              END + SUMMARIZE
            </button>
          )}
        </div>

        {plan && (
          <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
            {/* Transcript */}
            <div className="border border-slate-800 bg-slate-900 rounded-md">
              <div className="p-3 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center gap-2">
                LIVE TRANSCRIPT · {plan.candidate_name}
                {running && (
                  <span className="flex items-center gap-1 text-emerald-400 ml-auto">
                    <span className="pulse-dot" /> recording
                  </span>
                )}
              </div>
              <div className="p-4 space-y-4 max-h-[540px] overflow-y-auto">
                {turns.map((t, i) => (
                  <div key={i} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${KIND_TINT[t.question.kind] || KIND_TINT.opener}`}>
                        {t.question.kind.toUpperCase()}
                      </span>
                      <span className="text-slate-500 font-mono2 text-[10px]">
                        {String(i + 1).padStart(2, "0")} / {t.total_questions}
                      </span>
                      <span className="text-slate-500 font-mono2 text-[10px] ml-auto">
                        signal {Math.round(t.signal_strength * 100)}% · sentiment {Math.round(t.sentiment * 100)}%
                      </span>
                    </div>
                    <div className="text-[13px] text-slate-100">
                      <span className="font-mono2 text-indigo-400 mr-2">interviewer:</span>
                      {t.question.text}
                    </div>
                    <div className="text-[13px] text-slate-300 pl-6 border-l-2 border-slate-800">
                      <span className="font-mono2 text-emerald-400 mr-2">candidate:</span>
                      {t.mock_candidate_answer}
                    </div>
                    {t.star_extracted && (
                      <div className="pl-6 mt-1 text-[11px] font-mono2 text-slate-400 grid grid-cols-4 gap-1">
                        <div><span className="text-violet-400">S </span>{t.star_extracted.situation}</div>
                        <div><span className="text-violet-400">T </span>{t.star_extracted.task}</div>
                        <div><span className="text-violet-400">A </span>{t.star_extracted.action}</div>
                        <div><span className="text-violet-400">R </span>{t.star_extracted.result}</div>
                      </div>
                    )}
                    {t.suggested_followup && (
                      <div className="pl-6 text-[12px] text-amber-300 italic">
                        suggested follow-up: {t.suggested_followup}
                      </div>
                    )}
                  </div>
                ))}
                {turns.length === 0 && (
                  <div className="text-slate-500 text-[12px] text-center py-8">
                    Click Start to begin the simulated interview.
                  </div>
                )}
              </div>
            </div>

            {/* Running evaluation */}
            <div className="space-y-3">
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
                  RUNNING EVALUATION
                </div>
                {turns.length === 0 && (
                  <div className="text-slate-500 text-[12px]">No signals yet.</div>
                )}
                {turns.length > 0 && (
                  <div className="space-y-2">
                    {Object.entries(turns[turns.length - 1].running_evaluation).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-3">
                        <div className="w-28 text-[12px] text-slate-300 capitalize">
                          {k.replace(/_/g, " ")}
                        </div>
                        <div className="flex-1 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
                          <div className="h-full bg-cyan-400" style={{ width: `${v * 100}%` }} />
                        </div>
                        <div className="w-10 text-right font-mono2 text-[11px] text-slate-200">
                          {Math.round(v * 100)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {summary && (
                <div className="border border-emerald-500/30 bg-emerald-500/5 rounded-md p-4">
                  <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-2">
                    INTERVIEW SUMMARY
                  </div>
                  <div className="text-slate-100 text-[14px] font-display font-bold mb-1">
                    {summary.candidate_name}
                  </div>
                  <div className="text-[13px] text-slate-300 mb-3">
                    {summary.summary_narrative}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono2">
                    <div>
                      <div className="text-slate-500">signal</div>
                      <div className="text-emerald-300">{Math.round(summary.avg_signal * 100)}%</div>
                    </div>
                    <div>
                      <div className="text-slate-500">sentiment</div>
                      <div className="text-emerald-300">{Math.round(summary.avg_sentiment * 100)}%</div>
                    </div>
                    <div>
                      <div className="text-slate-500">recommendation</div>
                      <div className="text-slate-200">{summary.recommendation.replace(/_/g, " ")}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">confidence</div>
                      <div className="text-slate-200">{Math.round(summary.confidence * 100)}%</div>
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">STRENGTHS</div>
                    <ul className="text-[12px] text-slate-300 space-y-0.5 list-disc list-inside">
                      {summary.strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                  {summary.concerns.length > 0 && (
                    <div className="mt-2">
                      <div className="font-mono2 text-[10px] text-rose-400 mb-1">CONCERNS</div>
                      <ul className="text-[12px] text-rose-300 space-y-0.5 list-disc list-inside">
                        {summary.concerns.map((s, i) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
