import React from "react";
import useSWR from "swr";
import {
  BadgeDollarSign,
  Boxes,
  ClipboardCheck,
  Cpu,
  FileText,
  GitBranch,
  LineChart,
  MessageSquare,
  Mic,
  Radar,
  Radio,
  ScanSearch,
  ScrollText,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trophy,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const ICON_MAP = {
  MessageSquare, FileText, LineChart, Radar, ScrollText, Trophy, Send, Radio,
  ClipboardCheck, Mic, BadgeDollarSign, ShieldCheck, ScanSearch, GitBranch, Cpu,
  ShieldAlert, Sparkles,
};

const COL = {
  indigo: "border-indigo-500/30 text-indigo-300",
  emerald: "border-emerald-500/30 text-emerald-300",
  amber: "border-amber-500/30 text-amber-300",
  cyan: "border-cyan-500/30 text-cyan-300",
  violet: "border-violet-500/30 text-violet-300",
  rose: "border-rose-500/30 text-rose-300",
};

export default function Agents() {
  const { data: agents } = useSWR("/platform/agents", fetcher);
  const groups = {};
  for (const a of agents || []) {
    (groups[a.category] = groups[a.category] || []).push(a);
  }
  return (
    <AppLayout>
      <div data-testid={EAROS.agentsRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            AGENT REGISTRY
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Specialized AI agents on the platform
          </h1>
          <div className="text-slate-500 text-sm">
            Each agent is discoverable, health-checked, and version-controlled.
            The LLM never invokes an agent directly — the Runtime does, and
            every call is policy-gated.
          </div>
        </div>

        {Object.entries(groups).map(([cat, list]) => (
          <div key={cat}>
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 uppercase">
              {cat} · {list.length} agent{list.length > 1 ? "s" : ""}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {list.map((a) => {
                const Icon = ICON_MAP[a.icon] || Cpu;
                const col = COL[a.color] || COL.indigo;
                return (
                  <div
                    key={a.agent_id}
                    data-testid={EAROS.agentCard(a.agent_id)}
                    className={`border ${col.split(" ")[0]} bg-slate-900 rounded-md p-4`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${col.split(" ")[1]}`} strokeWidth={1.5} />
                        <div>
                          <div className="font-display text-[15px] font-bold text-slate-100 leading-tight">
                            {a.name}
                          </div>
                          <div className="font-mono2 text-[10px] text-slate-500">
                            {a.agent_id} · v{a.version}
                          </div>
                        </div>
                      </div>
                      <span className={`shrink-0 px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                        a.health === "healthy"
                          ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                          : "text-rose-400 border-rose-500/30 bg-rose-500/10"
                      }`}>
                        {a.health}
                      </span>
                    </div>
                    <div className="text-slate-400 text-[13px] mb-2 italic">
                      {a.tagline}
                    </div>
                    <div className="text-slate-500 text-[12px] mb-3">
                      {a.purpose}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[11px] font-mono2 mb-3">
                      <div>
                        <div className="text-slate-500">24h runs</div>
                        <div className="text-slate-200">{a.executions_24h}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">latency</div>
                        <div className="text-slate-200">{a.avg_latency_ms}ms</div>
                      </div>
                      <div>
                        <div className="text-slate-500">avg cost</div>
                        <div className="text-slate-200">${a.avg_cost_usd}</div>
                      </div>
                    </div>
                    <div className="text-[11px]">
                      <div className="font-mono2 text-slate-500 mb-1">INPUTS</div>
                      <div className="text-slate-300">
                        {a.inputs?.join(" · ") || "—"}
                      </div>
                      <div className="font-mono2 text-slate-500 mt-2 mb-1">OUTPUTS</div>
                      <div className="text-slate-300">
                        {a.outputs?.join(" · ") || "—"}
                      </div>
                      {a.depends_on_capabilities?.length > 0 && (
                        <>
                          <div className="font-mono2 text-slate-500 mt-2 mb-1">DEPENDS ON CAPABILITIES</div>
                          <div className="flex flex-wrap gap-1">
                            {a.depends_on_capabilities.map((c) => (
                              <span key={c} className="px-1.5 py-0.5 rounded-sm border border-slate-800 text-slate-400 font-mono2">
                                {c}
                              </span>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
