import React from "react";
import { EAROS } from "@/constants/testIds/earos";

// Skeleton loader — never let a real "0" look identical to "loading".
export function KpiSkeleton({ label, testId }) {
  return (
    <div
      data-testid={testId}
      className="p-3 border border-slate-800 bg-slate-900 rounded-md relative overflow-hidden"
    >
      <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
        {label}
      </div>
      <div className="mt-2 h-7 w-16 bg-slate-800 rounded-sm animate-pulse" />
      <div className="mt-2 h-3 w-24 bg-slate-800/60 rounded-sm animate-pulse" />
      <div className="absolute inset-x-0 top-0 h-0.5 bg-indigo-500/30 animate-pulse" />
    </div>
  );
}

export function TableSkeleton({ rows = 6 }) {
  return (
    <div className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden">
      <div className="divide-y divide-slate-800/60">
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="p-3 flex items-center gap-3">
            <div className="h-3 flex-1 bg-slate-800 rounded-sm animate-pulse"
                 style={{ width: `${60 + (i % 3) * 15}%` }} />
            <div className="h-3 w-16 bg-slate-800/60 rounded-sm animate-pulse" />
            <div className="h-3 w-10 bg-slate-800/60 rounded-sm animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton({ height = "h-40" }) {
  return (
    <div className={`border border-slate-800 bg-slate-900 rounded-md p-4 ${height} animate-pulse`}>
      <div className="h-3 w-24 bg-slate-800 rounded-sm mb-3" />
      <div className="h-3 w-full bg-slate-800/70 rounded-sm mb-2" />
      <div className="h-3 w-5/6 bg-slate-800/60 rounded-sm mb-2" />
      <div className="h-3 w-3/4 bg-slate-800/50 rounded-sm" />
    </div>
  );
}
