import React from "react";
import { CheckCircle2, ShieldAlert, Sparkles, Scale, TriangleAlert } from "lucide-react";
import { EAROS } from "@/constants/testIds/earos";

function ConfidenceGauge({ confidence }) {
  const v = Math.round((confidence?.value ?? 0) * 100);
  const bandColor =
    confidence?.band === "HIGH"
      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
      : confidence?.band === "MEDIUM"
        ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
        : "text-rose-400 border-rose-500/30 bg-rose-500/10";
  return (
    <div className="text-right">
      <div className={`font-mono2 text-3xl font-bold leading-none ${bandColor.split(" ")[0]}`}>
        {v}
        <span className="text-base text-slate-500">%</span>
      </div>
      <div
        className={`inline-block mt-1 px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] tracking-wider ${bandColor}`}
      >
        {confidence?.band} CONFIDENCE
      </div>
    </div>
  );
}

/**
 * The canonical AI Decision Card.
 * Zones: Recommendation, Confidence, Reasoning, Evidence, Tradeoffs, Risks, Policies, Action.
 */
export default function AIDecisionCard({ rec, onExecute, executing }) {
  if (!rec) return null;
  return (
    <div
      data-testid={EAROS.aiDecisionCard(rec.decision_id)}
      className="trace-beam relative border border-slate-800 bg-slate-900 rounded-md overflow-hidden"
    >
      <div className="p-4 border-b border-slate-800/80 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" strokeWidth={1.5} />
            <span className="font-mono2 text-[10px] tracking-widest text-indigo-400">
              AI_RECOMMENDATION
            </span>
            <span className="font-mono2 text-[10px] text-slate-500">
              {rec.decision_id}
            </span>
          </div>
          <h3 className="font-display text-lg text-slate-100 font-bold leading-tight">
            {rec.title}
          </h3>
          <p className="mt-1 text-slate-400 text-[13px] leading-relaxed">
            {rec.summary}
          </p>
        </div>
        <ConfidenceGauge confidence={rec.confidence} />
      </div>

      {/* Reasoning */}
      {rec.reasoning?.length > 0 && (
        <div className="p-4 border-b border-slate-800/60">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
            REASONING CHAIN
          </div>
          <ol className="space-y-2">
            {rec.reasoning.map((r, i) => (
              <li key={i} className="flex gap-3 text-[13px] leading-snug">
                <span className="font-mono2 text-indigo-400 shrink-0">
                  {String(r.step).padStart(2, "0")}
                </span>
                <div className="min-w-0">
                  <div className="text-slate-200">{r.thought}</div>
                  {r.conclusion && (
                    <div className="text-slate-500 text-[12px] mt-0.5">
                      → {r.conclusion}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Evidence + Tradeoffs + Risks — 3-col grid */}
      <div className="grid grid-cols-3 gap-0 border-b border-slate-800/60">
        <div className="p-4 border-r border-slate-800/60">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
            EVIDENCE
          </div>
          <ul className="space-y-1.5">
            {rec.evidence?.map((e, i) => (
              <li key={i} className="text-[12px] leading-tight">
                <div className="font-mono2 text-emerald-400">{e.source}</div>
                <div className="text-slate-300 truncate" title={e.excerpt}>
                  {e.excerpt || e.reference}
                </div>
              </li>
            ))}
            {!rec.evidence?.length && (
              <li className="text-slate-500 text-[12px]">no evidence</li>
            )}
          </ul>
        </div>
        <div className="p-4 border-r border-slate-800/60">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 flex items-center gap-1">
            <Scale className="w-3 h-3" strokeWidth={1.5} /> TRADEOFFS
          </div>
          <ul className="space-y-1 text-[12px] text-slate-300 list-disc list-inside">
            {rec.tradeoffs?.filter(Boolean).map((t, i) => <li key={i}>{t}</li>)}
            {!rec.tradeoffs?.filter(Boolean).length && (
              <li className="list-none text-slate-500">no tradeoffs surfaced</li>
            )}
          </ul>
        </div>
        <div className="p-4">
          <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 flex items-center gap-1">
            <TriangleAlert className="w-3 h-3" strokeWidth={1.5} /> RISKS
          </div>
          <ul className="space-y-1 text-[12px] text-rose-300 list-disc list-inside">
            {rec.risks?.filter(Boolean).map((r, i) => <li key={i}>{r}</li>)}
            {!rec.risks?.filter(Boolean).length && (
              <li className="list-none text-slate-500">no risks flagged</li>
            )}
          </ul>
        </div>
      </div>

      {/* Policies referenced */}
      {rec.policies_referenced?.length > 0 && (
        <div className="p-4 border-b border-slate-800/60 flex items-center gap-2 flex-wrap">
          <ShieldAlert className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.5} />
          <span className="font-mono2 text-[10px] tracking-widest text-slate-500">
            POLICIES:
          </span>
          {rec.policies_referenced.map((p) => (
            <span
              key={p.policy_id}
              className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                p.decision === "allow"
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                  : p.decision === "deny"
                    ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
                    : "text-amber-400 bg-amber-500/10 border-amber-500/30"
              }`}
              title={p.reason}
            >
              {p.name} · {p.decision}
            </span>
          ))}
        </div>
      )}

      {/* Action zone (human execution) */}
      <div className="p-4 flex items-center justify-between gap-4 bg-slate-950/40">
        <div className="min-w-0">
          <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-1">
            HUMAN EXECUTION
          </div>
          <div className="text-[12px] text-slate-300 truncate">
            <span className="font-mono2 text-emerald-400">action:</span>{" "}
            <span className="font-mono2">{rec.action}</span>
            {Object.keys(rec.inputs || {}).length > 0 && (
              <>
                {" "}
                <span className="text-slate-500 font-mono2 text-[11px]">
                  {JSON.stringify(rec.inputs).slice(0, 80)}
                </span>
              </>
            )}
          </div>
        </div>
        {onExecute && (
          <button
            data-testid={EAROS.approveBtn(rec.decision_id)}
            disabled={executing}
            onClick={() => onExecute(rec)}
            className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2 disabled:opacity-50 transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
            {executing ? "EXECUTING…" : "APPROVE & EXECUTE"}
          </button>
        )}
      </div>
    </div>
  );
}
