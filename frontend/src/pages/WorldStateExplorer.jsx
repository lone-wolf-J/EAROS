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

function Table({ rows, cols }) {
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
            {rows?.map((r, i) => (
              <tr key={i} className="hover:bg-slate-800/40">
                {cols.map((c) => (
                  <td key={c.key} className="px-3 py-2 text-slate-200">
                    {c.render ? c.render(r) : r[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
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

        <div className="flex gap-1 border-b border-slate-800/80 pb-0">
          {TABS.map((t) => (
            <button
              key={t.key}
              data-testid={EAROS.worldTab(t.key)}
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

        {tab === "org" && (
          <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
            <pre className="font-mono2 text-[12px] text-slate-200 whitespace-pre-wrap">
              {JSON.stringify(org || {}, null, 2)}
            </pre>
          </div>
        )}
        {tab === "departments" && (
          <Table
            rows={departments}
            cols={[
              { key: "name", label: "NAME" },
              { key: "leader_name", label: "LEADER" },
              { key: "headcount", label: "HEADCOUNT" },
              { key: "attrition_rate", label: "ATTRITION",
                render: (r) => `${(r.attrition_rate * 100).toFixed(1)}%` },
              { key: "health_score", label: "HEALTH",
                render: (r) => Math.round(r.health_score * 100) },
            ]}
          />
        )}
        {tab === "teams" && (
          <Table
            rows={teams}
            cols={[
              { key: "name", label: "TEAM" },
              { key: "manager_name", label: "MANAGER" },
              { key: "headcount", label: "HEADCOUNT" },
              { key: "open_seats", label: "OPEN SEATS" },
            ]}
          />
        )}
        {tab === "jobs" && (
          <Table
            rows={jobs}
            cols={[
              { key: "title", label: "TITLE" },
              { key: "location", label: "LOCATION" },
              { key: "level", label: "LEVEL" },
              { key: "priority", label: "PRIORITY" },
              { key: "status", label: "STATUS" },
              { key: "salary",
                label: "SALARY BAND",
                render: (r) => `${r.currency} ${r.salary_min.toLocaleString()}–${r.salary_max.toLocaleString()}` },
              { key: "opened_days_ago", label: "AGE (d)" },
            ]}
          />
        )}
        {tab === "candidates" && (
          <Table
            rows={candidates?.slice(0, 200)}
            cols={[
              { key: "full_name", label: "NAME" },
              { key: "current_title", label: "TITLE" },
              { key: "current_company", label: "COMPANY" },
              { key: "location", label: "LOCATION" },
              { key: "stage", label: "STAGE" },
              { key: "years_experience", label: "YRS",
                render: (r) => r.years_experience.toFixed(1) },
              { key: "expected",
                label: "EXPECTS",
                render: (r) => `${r.currency} ${(r.expected_salary / 1000).toFixed(0)}k` },
            ]}
          />
        )}
        {tab === "offers" && (
          <Table
            rows={offers}
            cols={[
              { key: "candidate_id", label: "CANDIDATE" },
              { key: "job_id", label: "JOB" },
              { key: "base_salary", label: "BASE" },
              { key: "status", label: "STATUS" },
              { key: "acceptance_probability", label: "ACCEPTANCE",
                render: (r) => `${Math.round((r.acceptance_probability || 0) * 100)}%` },
            ]}
          />
        )}
        {tab === "skills" && (
          <Table
            rows={skills}
            cols={[
              { key: "name", label: "SKILL" },
              { key: "category", label: "CATEGORY" },
              { key: "market_scarcity", label: "SCARCITY",
                render: (r) => `${Math.round(r.market_scarcity * 100)}%` },
            ]}
          />
        )}
      </div>
    </AppLayout>
  );
}
