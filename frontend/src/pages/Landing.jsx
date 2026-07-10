import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Cpu, GitBranch, ScrollText, ShieldCheck, Sparkles } from "lucide-react";
import { EAROS } from "@/constants/testIds/earos";
import { useAuth } from "@/contexts/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function loginWithGoogle() {
  const redirectUrl = window.location.origin + "/auth/callback";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
}

const CAPSULES = [
  {
    icon: GitBranch,
    label: "PLANNER",
    text: "LLM proposes structured, evidence-grounded plans — never executes.",
  },
  {
    icon: ShieldCheck,
    label: "POLICY ENGINE",
    text: "First-class policies gate every action; every eval is audited.",
  },
  {
    icon: Cpu,
    label: "RUNTIME",
    text: "Deterministic orchestrator with retries, checkpoints, and replay.",
  },
  {
    icon: ScrollText,
    label: "GOVERNANCE",
    text: "Immutable event log. Human approvals on hiring, offers, and strategy.",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const { devLogin } = useAuth();

  const runDemo = async (email) => {
    await devLogin(email);
    navigate("/dashboard");
  };

  return (
    <div
      data-testid={EAROS.landingHero}
      className="min-h-screen bg-slate-950 text-slate-100 relative overflow-hidden"
    >
      {/* grid backdrop */}
      <div
        className="absolute inset-0 opacity-[0.06] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.9) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.9) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div className="absolute top-0 right-0 w-[900px] h-[900px] bg-indigo-600/10 blur-3xl rounded-full -translate-y-1/2 translate-x-1/3 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-8 pt-10 pb-24">
        <div className="flex items-center justify-between mb-24">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-sm bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center">
              <Sparkles className="w-4.5 h-4.5 text-indigo-400" strokeWidth={1.5} />
            </div>
            <div>
              <div className="font-display text-xl font-black leading-none tracking-tight">
                EAROS
              </div>
              <div className="font-mono2 text-[10px] text-slate-500 mt-0.5">
                enterprise autonomous recruitment operating system
              </div>
            </div>
          </div>
          <button
            data-testid={EAROS.loginBtn}
            onClick={loginWithGoogle}
            className="flex items-center gap-2 px-4 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-200 text-sm transition-colors"
          >
            Sign in with Google
            <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="max-w-3xl">
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-4">
            v0.1 · LEVELSHIFT DEMO TENANT · INDIA & USA
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-black tracking-tight leading-[1.05] text-slate-50">
            An operating system for{" "}
            <span className="text-indigo-400">governed talent intelligence</span>.
          </h1>
          <p className="mt-6 text-slate-400 text-lg leading-relaxed max-w-2xl">
            EAROS separates intelligence from execution. Claude proposes; the
            runtime validates; policies gate; capabilities act; humans stay
            accountable. Every decision is explainable, every action auditable,
            every plan replayable.
          </p>

          <div className="mt-10 flex flex-wrap gap-3">
            <button
              onClick={loginWithGoogle}
              data-testid={EAROS.loginBtn + "-primary"}
              className="flex items-center gap-2 px-5 py-3 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-semibold transition-colors"
            >
              Enter with Google
              <ArrowRight className="w-4 h-4" strokeWidth={2} />
            </button>
            <div className="flex items-center gap-2">
              <span className="font-mono2 text-[11px] text-slate-500">DEMO ROLES:</span>
              <button
                data-testid={EAROS.demoRecruiterBtn}
                onClick={() => runDemo("demo.recruiter@levelshift.ai")}
                className="px-3 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2"
              >
                recruiter
              </button>
              <button
                data-testid={EAROS.demoManagerBtn}
                onClick={() => runDemo("demo.manager@levelshift.ai")}
                className="px-3 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2"
              >
                hiring_manager
              </button>
              <button
                data-testid={EAROS.demoExecutiveBtn}
                onClick={() => runDemo("demo.executive@levelshift.ai")}
                className="px-3 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2"
              >
                executive
              </button>
            </div>
          </div>
        </div>

        <div className="mt-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {CAPSULES.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.label}
                className="p-4 border border-slate-800 bg-slate-900/60 rounded-md"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-indigo-400" strokeWidth={1.5} />
                  <span className="font-mono2 text-[10px] tracking-widest text-indigo-400">
                    {c.label}
                  </span>
                </div>
                <div className="text-slate-300 text-[13px] leading-relaxed">
                  {c.text}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-5 border border-slate-800 bg-slate-900/60 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
              ARCHITECTURE FLOW
            </div>
            <pre className="font-mono2 text-[12px] leading-relaxed text-slate-300 whitespace-pre">{`Planner
   ↓  proposes plan + reasoning + confidence
Execution Runtime
   ↓  validates dependencies
Policy Engine
   ↓  authorizes / requires approval / denies
Capability Registry
   ↓  dispatches deterministic capability
World State
   ↓  emits immutable events
Reflection Intelligence`}</pre>
          </div>
          <div className="p-5 border border-slate-800 bg-slate-900/60 rounded-md">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
              LEVELSHIFT SEED FOOTPRINT
            </div>
            <div className="grid grid-cols-2 gap-y-2 text-[13px]">
              {[
                ["1", "organization"],
                ["5", "departments"],
                ["9", "teams"],
                ["12", "open reqs · IN + US"],
                ["150+", "candidates in pipeline"],
                ["6", "governed capabilities"],
                ["5", "first-class policies"],
                ["∞", "immutable events"],
              ].map(([n, t]) => (
                <React.Fragment key={t}>
                  <div className="font-display font-black text-2xl text-slate-100">
                    {n}
                  </div>
                  <div className="self-center text-slate-400 text-[12px]">{t}</div>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
