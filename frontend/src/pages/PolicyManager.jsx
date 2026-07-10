import React from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

export default function PolicyManager() {
  const { data: policies } = useSWR("/platform/policies", fetcher);

  return (
    <AppLayout>
      <div data-testid={EAROS.policyRoot} className="p-6 space-y-4">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            POLICY ENGINE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            First-class Policies
          </h1>
          <div className="text-slate-500 text-sm">
            Every capability execution is evaluated. Denials and approval
            requirements are immutable audit events.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {policies?.map((p) => (
            <div
              key={p.policy_id}
              data-testid={EAROS.policyRow(p.policy_id)}
              className="border border-slate-800 bg-slate-900 rounded-md p-4"
            >
              <div className="flex items-center justify-between mb-1">
                <div className="font-display text-base font-bold text-slate-100">
                  {p.name}
                </div>
                <span
                  className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                    p.enabled
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                      : "text-slate-500 bg-slate-800 border-slate-700"
                  }`}
                >
                  {p.enabled ? "ENABLED" : "DISABLED"}
                </span>
              </div>
              <div className="text-slate-400 text-[13px]">{p.description}</div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] font-mono2">
                <div>
                  <span className="text-slate-500">scope · </span>
                  <span className="text-slate-200">{p.scope}</span>
                </div>
                <div>
                  <span className="text-slate-500">roles · </span>
                  <span className="text-slate-200">
                    {p.applies_to_roles?.join(", ") || "*"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">min_conf · </span>
                  <span className="text-slate-200">
                    {p.min_confidence ?? "—"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">max_sens · </span>
                  <span className="text-slate-200">
                    {p.max_sensitivity ?? "—"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">approval · </span>
                  <span
                    className={
                      p.requires_human_approval
                        ? "text-amber-300"
                        : "text-slate-200"
                    }
                  >
                    {p.requires_human_approval ? "REQUIRED" : "auto"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">version · </span>
                  <span className="text-slate-200">v{p.version}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
