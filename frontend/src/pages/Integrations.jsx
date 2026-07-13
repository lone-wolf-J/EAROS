import React from "react";
import useSWR from "swr";
import { CheckCircle2, Clock, Globe, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const CAT_LABEL = {
  ats: "ATS",
  crm: "HRMS / CRM",
  job_board: "Job Boards",
  social: "Social & Developer",
  communication: "Communication",
  referral: "Referrals",
  community: "Community",
};

function statusChip(status) {
  const map = {
    connected: ["text-emerald-400 bg-emerald-500/10 border-emerald-500/30", "connected"],
    degraded: ["text-amber-400 bg-amber-500/10 border-amber-500/30", "degraded"],
    rate_limited: ["text-amber-400 bg-amber-500/10 border-amber-500/30", "rate-limited"],
    disconnected: ["text-rose-400 bg-rose-500/10 border-rose-500/30", "disconnected"],
  };
  const [cls, label] = map[status] || ["text-slate-400 border-slate-500/30 bg-slate-500/10", status];
  return (
    <span className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${cls}`}>
      {label.toUpperCase()}
    </span>
  );
}

function minutesAgo(iso) {
  const d = new Date(iso);
  const mins = Math.max(1, Math.round((Date.now() - d.getTime()) / 60000));
  return `${mins}m ago`;
}

export default function Integrations() {
  const { data: ints } = useSWR("/platform/integrations", fetcher);
  const groups = {};
  for (const i of ints || []) {
    (groups[i.category] = groups[i.category] || []).push(i);
  }

  const total = ints?.length || 0;
  const connected = ints?.filter((i) => i.connection_status === "connected").length || 0;
  const totalRecords = (ints || []).reduce((a, b) => a + (b.records_available || 0), 0);

  return (
    <AppLayout>
      <div data-testid={EAROS.integrationsRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            INTEGRATIONS
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Connected talent, comms, and HRMS systems
          </h1>
          <div className="text-slate-500 text-sm">
            EAROS composes across your entire tool graph. All connections are
            capability-scoped and permission-limited.{" "}
            <span className="text-amber-400">
              Two systems are shown in a simulated degraded state to demonstrate
              resilience — real production wiring would connect them.
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-4 border border-slate-800 bg-slate-900 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">TOTAL</div>
            <div className="mt-1 font-display font-black text-2xl">{total}</div>
          </div>
          <div className="p-4 border border-slate-800 bg-slate-900 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">CONNECTED</div>
            <div className="mt-1 font-display font-black text-2xl text-emerald-400">
              {connected}
            </div>
          </div>
          <div className="p-4 border border-slate-800 bg-slate-900 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">RECORDS AVAILABLE</div>
            <div className="mt-1 font-display font-black text-2xl">
              {totalRecords.toLocaleString()}
            </div>
          </div>
          <div className="p-4 border border-slate-800 bg-slate-900 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">CATEGORIES</div>
            <div className="mt-1 font-display font-black text-2xl">
              {Object.keys(groups).length}
            </div>
          </div>
        </div>

        {Object.entries(groups).map(([cat, list]) => (
          <div key={cat}>
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2 uppercase">
              {CAT_LABEL[cat] || cat}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {list.map((i) => (
                <div
                  key={i.integration_id}
                  data-testid={EAROS.integrationCard(i.integration_id)}
                  className="border border-slate-800 bg-slate-900 rounded-md p-4"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-8 h-8 rounded-sm flex items-center justify-center font-display font-black text-sm"
                        style={{ background: `${i.color}20`, color: i.color, border: `1px solid ${i.color}40` }}
                      >
                        {i.name.slice(0, 2)}
                      </div>
                      <div>
                        <div className="text-slate-100 text-[13px] font-medium">{i.name}</div>
                        <div className="font-mono2 text-[10px] text-slate-500">
                          {i.integration_id}
                        </div>
                      </div>
                    </div>
                    {statusChip(i.connection_status)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono2 mt-2">
                    <div className="flex items-center gap-1 text-slate-400">
                      <Clock className="w-3 h-3" strokeWidth={1.5} />
                      {minutesAgo(i.last_sync)}
                    </div>
                    <div className="text-slate-400">
                      <span className="text-slate-500">latency </span>
                      {i.latency_ms}ms
                    </div>
                    <div className="text-slate-400 col-span-2">
                      <span className="text-slate-500">records </span>
                      {i.records_available.toLocaleString()}
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-1 flex-wrap text-[10px] font-mono2">
                    <Globe className="w-3 h-3 text-slate-500" strokeWidth={1.5} />
                    {i.coverage_geo.map((g) => (
                      <span key={g} className="px-1 py-0.5 rounded-sm border border-slate-800 text-slate-400">
                        {g}
                      </span>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center gap-1 flex-wrap text-[10px] font-mono2">
                    <ShieldCheck className="w-3 h-3 text-slate-500" strokeWidth={1.5} />
                    {i.permissions?.map((p) => (
                      <span key={p} className="px-1 py-0.5 rounded-sm border border-slate-800 text-slate-400">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
