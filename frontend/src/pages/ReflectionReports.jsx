import React from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function ReflectionReports() {
  const { data: reports } = useSWR("/reflection/reports", fetcher);

  return (
    <AppLayout>
      <div data-testid={EAROS.reflectionRoot} className="p-6 space-y-4">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            REFLECTION
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Learn without rewriting history
          </h1>
          <div className="text-slate-500 text-sm">
            Auto-generated after every terminal execution. Proposes future
            improvements — does not alter events or state.
          </div>
        </div>

        <div className="space-y-3">
          {reports?.length === 0 && (
            <div className="p-6 border border-slate-800 bg-slate-900 rounded-md text-slate-500 text-[13px]">
              No reflections yet. Execute a plan to generate one.
            </div>
          )}
          {reports?.map((r) => (
            <div
              key={r.reflection_id}
              data-testid={EAROS.reflectionRow(r.reflection_id)}
              className="border border-slate-800 bg-slate-900 rounded-md p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="font-display text-base font-bold text-slate-100">
                    {r.what_happened}
                  </div>
                  <div className="font-mono2 text-[10px] text-slate-500 mt-0.5">
                    {r.reflection_id} · exec {r.execution_id} · {r.created_at?.slice(0, 19)}
                  </div>
                </div>
                <div className="flex gap-2 text-[11px] font-mono2">
                  {Object.entries(r.metrics || {}).map(([k, v]) => (
                    <div key={k} className="px-2 py-1 border border-slate-800 rounded-sm">
                      <div className="text-slate-500 text-[9px]">{k}</div>
                      <div className="text-slate-200">{v}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="text-slate-400 text-[12px] mb-3">{r.why}</div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-1">
                    SUCCEEDED
                  </div>
                  <ul className="text-[12px] text-slate-300 space-y-0.5 list-disc list-inside">
                    {r.what_succeeded?.length
                      ? r.what_succeeded.map((s, i) => <li key={i}>{s}</li>)
                      : <li className="list-none text-slate-500">—</li>}
                  </ul>
                </div>
                <div>
                  <div className="font-mono2 text-[10px] tracking-widest text-rose-400 mb-1">
                    FAILED
                  </div>
                  <ul className="text-[12px] text-slate-300 space-y-0.5 list-disc list-inside">
                    {r.what_failed?.length
                      ? r.what_failed.map((s, i) => <li key={i}>{s}</li>)
                      : <li className="list-none text-slate-500">—</li>}
                  </ul>
                </div>
                <div>
                  <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-1">
                    IMPROVEMENTS
                  </div>
                  <ul className="text-[12px] text-slate-300 space-y-0.5 list-disc list-inside">
                    {r.improvements?.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
