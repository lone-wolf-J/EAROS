import React, { useState } from "react";
import useSWR from "swr";
import { CheckCircle2, ShieldCheck, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const EVENT_TINT = {
  "policy.evaluated": "text-slate-300",
  "policy.violated": "text-rose-400",
  "runtime.execution.started": "text-indigo-300",
  "runtime.execution.completed": "text-emerald-400",
  "runtime.execution.failed": "text-rose-400",
  "runtime.step.started": "text-slate-400",
  "runtime.step.completed": "text-emerald-300",
  "governance.approval.requested": "text-amber-400",
  "governance.approval.granted": "text-emerald-400",
  "governance.approval.denied": "text-rose-400",
  "reflection.created": "text-violet-300",
};

export default function Governance() {
  const { data: events, mutate: mutateEvents } = useSWR("/governance/events?limit=100", fetcher, {
    refreshInterval: 5000,
  });
  const { data: approvals, mutate: mutateApprovals } = useSWR(
    "/governance/approvals",
    fetcher,
    { refreshInterval: 5000 },
  );
  const [decidingId, setDecidingId] = useState(null);

  const decide = async (id, decision) => {
    setDecidingId(id);
    try {
      await api.post(`/governance/approvals/${id}/decide`, { decision });
      await Promise.all([mutateApprovals(), mutateEvents()]);
    } finally {
      setDecidingId(null);
    }
  };

  const pendingApprovals = approvals?.filter((a) => a.status === "pending") || [];
  const decidedApprovals = approvals?.filter((a) => a.status !== "pending") || [];

  return (
    <AppLayout>
      <div data-testid={EAROS.governanceRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            GOVERNANCE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Audit & Approvals
          </h1>
          <div className="text-slate-500 text-sm">
            Immutable event stream · replayable · human-accountable.
          </div>
        </div>

        {/* 30-second exec explainer */}
        <div className="border border-indigo-500/30 bg-indigo-500/5 rounded-md p-4">
          <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-2">
            GOVERNANCE IN 30 SECONDS
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[13px] text-slate-300">
            <div>
              <div className="text-slate-100 font-medium mb-1">Immutability</div>
              Every AI action writes an append-only event. Nothing can be
              edited or deleted — including by the AI itself. Auditors get a
              cryptographically-orderable log by design.
            </div>
            <div>
              <div className="text-slate-100 font-medium mb-1">Human accountability</div>
              Compensation, shortlists, offers, and compliance exceptions
              cannot be finalized by the AI. Policies force those actions
              through a human approver whose name is recorded.
            </div>
            <div>
              <div className="text-slate-100 font-medium mb-1">Replayability</div>
              Any decision can be reconstructed from its events, including
              which policies fired, which capabilities ran, and which
              approver said yes. Try the <span className="font-mono2 text-indigo-300">Agent Deep-Dive</span> page.
            </div>
          </div>
        </div>

        {/* Approvals */}
        <div className="border border-slate-800 bg-slate-900 rounded-md">
          <div className="p-4 border-b border-slate-800/60 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              APPROVAL QUEUE
            </div>
            <div className="ml-auto font-mono2 text-[11px] text-amber-400">
              {pendingApprovals.length} pending
            </div>
          </div>
          <div className="divide-y divide-slate-800/60">
            {pendingApprovals.map((a) => (
              <div
                key={a.approval_id}
                data-testid={EAROS.approvalRow(a.approval_id)}
                className="p-4 flex items-start justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="text-slate-100 text-[13px] font-medium">
                    {a.subject_type} · {a.subject_id}
                  </div>
                  <div className="text-slate-400 text-[12px] mt-1">{a.reason}</div>
                  <div className="font-mono2 text-[10px] text-slate-500 mt-1">
                    requested_by · {a.requested_by} · {a.created_at?.slice(0, 19)}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    data-testid={EAROS.approvalGrantBtn(a.approval_id)}
                    disabled={decidingId === a.approval_id}
                    onClick={() => decide(a.approval_id, "granted")}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-sm bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[12px] font-mono2 disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                    GRANT
                  </button>
                  <button
                    data-testid={EAROS.approvalDenyBtn(a.approval_id)}
                    disabled={decidingId === a.approval_id}
                    onClick={() => decide(a.approval_id, "denied")}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-sm bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-[12px] font-mono2 disabled:opacity-50"
                  >
                    <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                    DENY
                  </button>
                </div>
              </div>
            ))}
            {pendingApprovals.length === 0 && (
              <div className="p-6 text-center text-slate-500 text-[12px]">
                No pending approvals.
              </div>
            )}
          </div>
        </div>

        {/* Decided approvals — brief */}
        {decidedApprovals.length > 0 && (
          <div className="border border-slate-800 bg-slate-900 rounded-md">
            <div className="p-4 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500">
              APPROVAL HISTORY
            </div>
            <div className="divide-y divide-slate-800/60 max-h-48 overflow-y-auto">
              {decidedApprovals.slice(0, 20).map((a) => (
                <div key={a.approval_id} className="p-3 flex items-center gap-3 text-[12px]">
                  <span
                    className={`font-mono2 text-[10px] px-1.5 py-0.5 rounded-sm border ${
                      a.status === "granted"
                        ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                        : "text-rose-400 bg-rose-500/10 border-rose-500/30"
                    }`}
                  >
                    {a.status.toUpperCase()}
                  </span>
                  <span className="text-slate-300 truncate flex-1">{a.reason}</span>
                  <span className="font-mono2 text-slate-500 text-[10px]">
                    {a.decided_by || "-"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Event stream */}
        <div className="border border-slate-800 bg-slate-900 rounded-md">
          <div className="p-4 border-b border-slate-800/60 font-mono2 text-[10px] tracking-widest text-slate-500 flex items-center justify-between">
            <span>IMMUTABLE EVENT STREAM</span>
            <span>{events?.length || 0} events</span>
          </div>
          <div className="divide-y divide-slate-800/40 max-h-[560px] overflow-y-auto">
            {events?.map((e) => (
              <div
                key={e.event_id}
                data-testid={EAROS.eventRow(e.event_id)}
                className="p-2.5 grid grid-cols-[140px_180px_1fr_120px] gap-3 items-center text-[11px]"
              >
                <span className="font-mono2 text-slate-500">
                  {e.occurred_at?.slice(11, 19)}
                </span>
                <span
                  className={`font-mono2 ${EVENT_TINT[e.event_type] || "text-slate-300"}`}
                >
                  {e.event_type}
                </span>
                <span className="text-slate-400 truncate font-mono2 text-[11px]">
                  {e.subject_type}:{e.subject_id}{" "}
                  {e.payload && (
                    <span className="text-slate-500">
                      · {JSON.stringify(e.payload).slice(0, 80)}
                    </span>
                  )}
                </span>
                <span className="font-mono2 text-slate-500 text-right truncate">
                  {e.actor || "-"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
