import React, { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const TABS = [
  { key: "org", label: "Organization" },
  { key: "departments", label: "Departments" },
  { key: "teams", label: "Teams" },
  { key: "jobs", label: "Jobs" },
  { key: "candidates", label: "Candidates" },
  { key: "offers", label: "Offers" },
  { key: "skills", label: "Skills" },
];

function Table({ rows, cols, empty = "No data." }) {
  if (!rows) {
    return (
      <div className="border border-slate-800 bg-slate-900 rounded-md p-8 text-center font-mono2 text-[11px] text-slate-500">
        loading…
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="border border-slate-800 bg-slate-900 rounded-md p-8 text-center font-mono2 text-[11px] text-slate-500">
        {empty}
      </div>
    );
  }
  return (
    <div className="border border-slate-800 bg-slate-900 rounded-md overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead className="bg-slate-950 text-slate-500 font-mono2">
            <tr>
              {cols.map((c) => (
                <th key={c.key} className="text-left px-3 py-2 whitespace-nowrap">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {rows.map((r, i) => (
              <tr key={r.id || r.job_id || r.candidate_id || r.department_id || r.team_id || r.skill_id || r.offer_id || i}
                  className="hover:bg-slate-800/40">
                {cols.map((c) => (
                  <td key={c.key} className="px-3 py-2 text-slate-200">
                    {c.render ? c.render(r) : r[c.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-3 py-1.5 border-t border-slate-800/60 text-[10px] font-mono2 text-slate-500">
        {rows.length} record{rows.length === 1 ? "" : "s"}
      </div>
    </div>
  );
}

function OrgCard({ org, departments, teams, jobs, candidates }) {
  if (!org) {
    return (
      <div className="border border-slate-800 bg-slate-900 rounded-md p-8 text-center font-mono2 text-[11px] text-slate-500">
        loading organization…
      </div>
    );
  }
  const kpis = [
    ["HEADCOUNT", org.total_headcount],
    ["ACTIVE REQS", org.active_reqs],
    ["DEPARTMENTS", departments?.length ?? "—"],
    ["TEAMS", teams?.length ?? "—"],
    ["OPEN JOBS", jobs?.filter((j) => j.status === "open").length ?? "—"],
    ["CANDIDATES", candidates?.length ?? "—"],
  ];
  return (
    <div className="border border-slate-800 bg-slate-900 rounded-md p-5 space-y-4">
      <div>
        <div className="font-mono2 text-[10px] tracking-widest text-indigo-400 mb-1">
          ORGANIZATION
        </div>
        <div className="font-display text-2xl font-black text-slate-100">
          {org.name}
        </div>
        <div className="text-slate-400 text-[13px]">
          {org.industry} · {org.headquarters} · {org.domain}
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {kpis.map(([k, v]) => (
          <div key={k} className="p-3 border border-slate-800 rounded-sm bg-slate-950">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              {k}
            </div>
            <div className="mt-1 font-display font-black text-xl text-slate-100">
              {v}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WorldStateExplorer() {
  const [tab, setTab] = useState("jobs");
  const { data: org } = useSWR("/world/organization", fetcher);
  const { data: departments } = useSWR("/world/departments", fetcher);
  const { data: teams } = useSWR("/world/teams", fetcher);
  const { data: jobs } = useSWR("/world/jobs", fetcher);
  const { data: candidates } = useSWR("/world/candidates", fetcher);
  const { data: offers } = useSWR("/world/offers", fetcher);
  const { data: skills } = useSWR("/world/skills", fetcher);

  const jobById = React.useMemo(() => {
    const m = new Map();
    (jobs || []).forEach((j) => m.set(j.job_id, j));
    return m;
  }, [jobs]);
  const candById = React.useMemo(() => {
    const m = new Map();
    (candidates || []).forEach((c) => m.set(c.candidate_id, c));
    return m;
  }, [candidates]);
  const deptById = React.useMemo(() => {
    const m = new Map();
    (departments || []).forEach((d) => m.set(d.department_id, d));
    return m;
  }, [departments]);

  return (
    <AppLayout>
      <div data-testid={EAROS.worldRoot} className="p-6 space-y-4">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1">
            WORLD STATE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Single source of truth
          </h1>
          <div className="text-slate-500 text-sm">
            Everything the Planner reasons against. Read-only outside the Runtime.
          </div>
        </div>

        <div className="flex gap-1 border-b border-slate-800/80 pb-0 flex-wrap">
          {TABS.map((t) => (
            <button
              key={t.key}
              data-testid={EAROS.worldTab(t.key)}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 text-[12px] font-mono2 border-b-2 -mb-px transition-colors ${
                tab === t.key
                  ? "border-indigo-500 text-slate-100"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content — keyed so React fully re-mounts on tab change */}
        <div key={tab}>
          {tab === "org" && (
            <OrgCard org={org} departments={departments} teams={teams}
                     jobs={jobs} candidates={candidates} />
          )}

          {tab === "departments" && (
            <Table
              rows={departments}
              empty="No departments seeded."
              cols={[
                { key: "name", label: "NAME" },
                { key: "leader_name", label: "LEADER" },
                { key: "headcount", label: "HEADCOUNT" },
                { key: "attrition_rate", label: "ATTRITION",
                  render: (r) => `${(r.attrition_rate * 100).toFixed(1)}%` },
                { key: "health_score", label: "HEALTH SCORE",
                  render: (r) => Math.round(r.health_score * 100) },
              ]}
            />
          )}

          {tab === "teams" && (
            <Table
              rows={teams}
              empty="No teams seeded."
              cols={[
                { key: "name", label: "TEAM" },
                { key: "department", label: "DEPARTMENT",
                  render: (r) => deptById.get(r.department_id)?.name || "—" },
                { key: "manager_name", label: "MANAGER" },
                { key: "headcount", label: "HEADCOUNT" },
                { key: "open_seats", label: "OPEN SEATS",
                  render: (r) => (
                    <span className={r.open_seats > 0 ? "text-amber-400" : "text-slate-300"}>
                      {r.open_seats}
                    </span>
                  ) },
              ]}
            />
          )}

          {tab === "jobs" && (
            <Table
              rows={jobs}
              empty="No jobs open."
              cols={[
                { key: "title", label: "TITLE" },
                { key: "location", label: "LOCATION" },
                { key: "level", label: "LEVEL" },
                { key: "priority", label: "PRIORITY",
                  render: (r) => (
                    <span className={`px-1.5 py-0.5 rounded-sm border font-mono2 text-[10px] ${
                      r.priority === "P0" ? "text-rose-400 border-rose-500/30 bg-rose-500/10" :
                      r.priority === "P1" ? "text-amber-400 border-amber-500/30 bg-amber-500/10" :
                      "text-slate-400 border-slate-500/30 bg-slate-500/10"
                    }`}>{r.priority}</span>) },
                { key: "status", label: "STATUS" },
                { key: "salary", label: "SALARY BAND",
                  render: (r) => `${r.currency} ${r.salary_min.toLocaleString()}–${r.salary_max.toLocaleString()}` },
                { key: "opened_days_ago", label: "AGE (d)" },
              ]}
            />
          )}

          {tab === "candidates" && (
            <Table
              rows={candidates?.slice(0, 300)}
              empty="No candidates in pipeline."
              cols={[
                { key: "full_name", label: "NAME" },
                { key: "current_title", label: "TITLE" },
                { key: "current_company", label: "COMPANY" },
                { key: "job", label: "ROLE",
                  render: (r) => jobById.get(r.job_id)?.title || "—" },
                { key: "location", label: "LOCATION" },
                { key: "stage", label: "STAGE",
                  render: (r) => <span className="font-mono2 text-[11px]">{r.stage}</span> },
                { key: "years_experience", label: "YRS",
                  render: (r) => r.years_experience?.toFixed(1) },
                { key: "expected", label: "EXPECTS",
                  render: (r) => `${r.currency} ${(r.expected_salary / 1000).toFixed(0)}k` },
              ]}
            />
          )}

          {tab === "offers" && (
            <Table
              rows={offers}
              empty="No offers yet — try Recruiter Copilot or the Java Chennai scenario."
              cols={[
                { key: "candidate", label: "CANDIDATE",
                  render: (r) => candById.get(r.candidate_id)?.full_name || r.candidate_id },
                { key: "job", label: "ROLE",
                  render: (r) => jobById.get(r.job_id)?.title || "—" },
                { key: "base", label: "BASE",
                  render: (r) => `${r.currency} ${r.base_salary?.toLocaleString?.() ?? "—"}` },
                { key: "status", label: "STATUS" },
                { key: "acceptance", label: "ACCEPTANCE",
                  render: (r) => `${Math.round((r.acceptance_probability || 0) * 100)}%` },
                { key: "market", label: "MARKET PCTILE",
                  render: (r) => `${Math.round((r.market_percentile || 0) * 100)}%` },
              ]}
            />
          )}

          {tab === "skills" && (
            <Table
              rows={skills}
              empty="No skills taxonomy loaded."
              cols={[
                { key: "name", label: "SKILL" },
                { key: "category", label: "CATEGORY" },
                { key: "market_scarcity", label: "MARKET SCARCITY",
                  render: (r) => (
                    <span className={r.market_scarcity > 0.75 ? "text-rose-400" :
                                     r.market_scarcity > 0.55 ? "text-amber-400" : "text-emerald-400"}>
                      {Math.round(r.market_scarcity * 100)}%
                    </span>
                  ) },
              ]}
            />
          )}
        </div>
      </div>
    </AppLayout>
  );
}
