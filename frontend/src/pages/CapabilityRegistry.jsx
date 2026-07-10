import React from "react";
import useSWR from "swr";
import { Boxes, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function CapabilityRegistry() {
  const { data: caps } = useSWR("/platform/capabilities", fetcher);

  return (
    <AppLayout>
      <div data-testid={EAROS.capabilityRoot} className="p-6 space-y-4">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            CAPABILITY REGISTRY
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Deterministic Capabilities
          </h1>
          <div className="text-slate-500 text-sm">
            Discoverable · replaceable · independently deployable. The LLM
            never invokes these directly — the Runtime does.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {caps?.map((c) => (
            <div
              key={c.capability_id}
              data-testid={EAROS.capabilityRow(c.capability_id)}
              className="border border-slate-800 bg-slate-900 rounded-md p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Boxes className="w-4 h-4 text-indigo-400" strokeWidth={1.5} />
                    <div className="font-display text-base font-bold text-slate-100">
                      {c.name}
                    </div>
                  </div>
                  <div className="font-mono2 text-[11px] text-slate-500 mt-0.5">
                    {c.capability_id} · v{c.version}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <span
                    className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                      c.health === "healthy"
                        ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                        : "text-rose-400 bg-rose-500/10 border-rose-500/30"
                    }`}
                  >
                    {c.health.toUpperCase()}
                  </span>
                  <span className="px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] text-slate-400 bg-slate-500/10 border-slate-500/30">
                    {c.category}
                  </span>
                </div>
              </div>
              <div className="text-slate-400 text-[13px]">{c.description}</div>

              <div className="mt-3 grid grid-cols-2 gap-3 text-[11px]">
                <div>
                  <div className="font-mono2 text-slate-500 mb-1">INPUTS</div>
                  <ul className="space-y-0.5">
                    {Object.entries(c.inputs || {}).map(([k, v]) => (
                      <li key={k} className="font-mono2 text-slate-300">
                        <span className="text-indigo-400">{k}</span>
                        <span className="text-slate-500">: {v}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="font-mono2 text-slate-500 mb-1">OUTPUTS</div>
                  <ul className="space-y-0.5">
                    {Object.entries(c.outputs || {}).map(([k, v]) => (
                      <li key={k} className="font-mono2 text-slate-300">
                        <span className="text-emerald-400">{k}</span>
                        <span className="text-slate-500">: {v}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <ShieldAlert className="w-3 h-3 text-slate-500" strokeWidth={1.5} />
                {c.permissions?.map((p) => (
                  <span
                    key={p}
                    className="px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] text-slate-400 border-slate-800 bg-slate-950"
                  >
                    {p}
                  </span>
                ))}
                <span className="ml-auto font-mono2 text-[10px] text-slate-500">
                  sensitivity · {c.sensitivity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
