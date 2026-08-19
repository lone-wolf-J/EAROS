import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  Boxes,
  Building2,
  ClipboardList,
  Cpu,
  FileWarning,
  Gauge,
  GitBranch,
  Headphones,
  History,
  Layers,
  LogOut,
  Radar,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Users2,
} from "lucide-react";
import { EAROS } from "@/constants/testIds/earos";
import { useAuth } from "@/contexts/AuthContext";

const NAV = [
  { key: "mission", to: "/mission", label: "Mission Control", icon: Radar, group: "APPS" },
  { key: "scenarios", to: "/scenarios", label: "Demo Scenarios", icon: Sparkles, group: "APPS" },
  { key: "intake", to: "/intake", label: "Hiring Intake", icon: Headphones, group: "APPS" },
  { key: "dashboard", to: "/dashboard", label: "Hiring Dashboard", icon: Gauge, group: "APPS" },
  { key: "ats", to: "/ats", label: "ATS Operations", icon: ClipboardList, group: "APPS" },
  { key: "recruiter", to: "/recruiter", label: "Recruiter Copilot", icon: Users2, group: "APPS" },
  { key: "sourcing", to: "/sourcing", label: "Sourcing", icon: Radar, group: "APPS" },
  { key: "resume", to: "/resume", label: "Resume Studio", icon: ScrollText, group: "APPS" },
  { key: "outreach", to: "/outreach", label: "Outreach Studio", icon: Boxes, group: "APPS" },
  { key: "screening", to: "/interview", label: "AI Interview Suite", icon: Headphones, group: "APPS" },
  { key: "executive", to: "/executive", label: "Executive Copilot", icon: Sparkles, group: "APPS" },
  { key: "candidate", to: "/candidate", label: "Candidate Assistant", icon: Headphones, group: "APPS" },

  { key: "planner", to: "/planner", label: "Planner", icon: GitBranch, group: "INTELLIGENCE" },
  { key: "ats-workflows", to: "/ats/workflows", label: "ATS Autonomy", icon: GitBranch, group: "INTELLIGENCE" },
  { key: "deep-dive", to: "/deep-dive", label: "Agent Deep-Dive", icon: History, group: "INTELLIGENCE" },
  { key: "agents", to: "/agents", label: "Agent Registry", icon: Cpu, group: "INTELLIGENCE" },
  { key: "integrations", to: "/integrations", label: "Integrations", icon: Layers, group: "INTELLIGENCE" },

  { key: "world", to: "/world", label: "World State", icon: Building2, group: "PLATFORM" },
  { key: "capabilities", to: "/capabilities", label: "Capabilities", icon: Boxes, group: "PLATFORM" },
  { key: "policies", to: "/policies", label: "Policies", icon: FileWarning, group: "PLATFORM" },
  { key: "governance", to: "/governance", label: "Governance", icon: ScrollText, group: "PLATFORM" },
  { key: "enterprise-controls", to: "/enterprise-controls", label: "Enterprise Controls", icon: ShieldCheck, group: "PLATFORM" },
  { key: "reflection", to: "/reflection", label: "Reflection", icon: History, group: "PLATFORM" },
];

function Sidebar() {
  const groups = ["APPS", "INTELLIGENCE", "PLATFORM"];
  return (
    <aside
      data-testid={EAROS.sidebar}
      className="w-60 shrink-0 bg-slate-950 border-r border-slate-800/80 flex flex-col"
    >
      <div className="h-14 flex items-center gap-2 px-4 border-b border-slate-800/80">
        <div className="w-7 h-7 rounded-sm bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center">
          <Radar className="w-4 h-4 text-indigo-400" strokeWidth={1.5} />
        </div>
        <div className="leading-tight">
          <div className="font-display text-slate-100 text-sm font-black tracking-tight">
            EAROS
          </div>
          <div className="font-mono2 text-[10px] text-slate-500">
            recruitment.os / v0.1
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {groups.map((g) => (
          <div key={g} className="mb-4">
            <div className="px-4 mb-1 text-[10px] font-mono2 tracking-widest text-slate-500">
              {g}
            </div>
            {NAV.filter((n) => n.group === g).map((n) => {
              const Icon = n.icon;
              return (
                <NavLink
                  key={n.key}
                  to={n.to}
                  data-testid={EAROS.navItem(n.key)}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 text-[13px] transition-colors border-l-2 ${
                      isActive
                        ? "bg-slate-900 text-slate-100 border-l-indigo-500"
                        : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/60 border-l-transparent"
                    }`
                  }
                >
                  <Icon className="w-4 h-4" strokeWidth={1.5} />
                  <span className="font-medium">{n.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-slate-800/80 text-[11px] font-mono2 text-slate-500 space-y-1">
        <div className="flex items-center gap-2">
          <span className="pulse-dot" />
          <span>runtime.healthy</span>
        </div>
        <div className="flex items-center gap-2">
          <Cpu className="w-3 h-3" strokeWidth={1.5} />
          <span>claude-sonnet-4.5</span>
        </div>
        <div className="flex items-center gap-2">
          <Layers className="w-3 h-3" strokeWidth={1.5} />
          <span>tenant: LevelShift</span>
        </div>
      </div>
    </aside>
  );
}

function TopNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <header
      data-testid={EAROS.topNav}
      className="h-14 border-b border-slate-800/80 bg-slate-950 flex items-center justify-between px-6"
    >
      <div className="flex items-center gap-3">
        <Activity className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
        <div className="font-mono2 text-[11px] text-slate-500">
          intelligence separated from execution · every decision auditable
        </div>
        <span className="px-1.5 py-0.5 rounded-sm border border-amber-500/40 bg-amber-500/10 text-amber-300 font-mono2 text-[10px] tracking-widest">
          DEMO · SYNTHETIC DATA
        </span>
      </div>
      <div className="flex items-center gap-3">
        {user?.picture && (
          <img
            src={user.picture}
            alt=""
            className="w-6 h-6 rounded-sm border border-slate-800 object-cover"
          />
        )}
        <div className="text-right leading-tight">
          <div className="text-sm text-slate-100 font-medium">{user?.name}</div>
          <div className="font-mono2 text-[10px] text-indigo-400 uppercase">
            {user?.role}
          </div>
        </div>
        <button
          data-testid={EAROS.logoutBtn}
          onClick={async () => {
            await logout();
            navigate("/");
          }}
          className="ml-2 flex items-center gap-1 px-2 py-1 border border-slate-800 rounded-sm text-slate-400 hover:text-slate-100 hover:border-slate-700 text-[12px]"
        >
          <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />
          Sign out
        </button>
      </div>
    </header>
  );
}

export default function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
