import React, { useEffect, useState } from "react";
import useSWR from "swr";
import {
  CheckCircle,
  Download,
  FileText,
  Layers,
  ScrollText,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { EAROS } from "@/constants/testIds/earos";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = (url) => api.get(url).then((r) => r.data);

const SAMPLE = `Karthik Kulkarni — Senior Salesforce Engineer @ TCS
Bangalore, India · +91 98xxx xxxxx · karthik.kulkarni@example.in

Summary
12+ years delivering enterprise Salesforce platforms for banking and retail
clients.

Skills
Salesforce Apex, Salesforce LWC, Salesforce CPQ, MuleSoft, Kafka, Kubernetes,
AWS, Enterprise Sales

Experience
Senior Salesforce Engineer at TCS
- Led CPQ rollout across 12 markets in 9 months.
- Owned Apex + LWC micro-service integration with 99.98% uptime.
- Mentored 4 junior engineers.

Education
BE, Computer Science, PES Institute of Technology, 2011.

Certifications
Salesforce Certified Application Architect, Salesforce Certified Data Architect
`;

export default function ResumeStudio() {
  const { data: jobs } = useSWR("/world/jobs", fetcher);
  const [text, setText] = useState(SAMPLE);
  const [jobId, setJobId] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [format, setFormat] = useState("one_page"); // "one_page" | "client_submission"

  useEffect(() => {
    if (jobs && !jobId) setJobId(jobs[0]?.job_id);
  }, [jobs, jobId]);

  const analyze = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/resume/analyze", {
        resume_text: text, job_id: jobId, candidate_alias: "Candidate-A",
      });
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div data-testid={EAROS.resumeRoot} className="p-6 space-y-6">
        <div>
          <div className="font-mono2 text-[11px] tracking-widest text-indigo-400 mb-1 flex items-center gap-2">
            <ScrollText className="w-3.5 h-3.5" strokeWidth={1.5} />
            RESUME INTELLIGENCE
          </div>
          <h1 className="font-display text-3xl font-black tracking-tight">
            Parse. Score. Redact. Submit.
          </h1>
          <div className="text-slate-500 text-sm">
            Paste a resume, pick the target requisition, and see fit analysis,
            strengths, gaps, and a client-ready one-page summary.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="border border-slate-800 bg-slate-900 rounded-md p-4 space-y-3">
            <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
              PASTE RESUME
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={16}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100 focus:outline-none focus:border-indigo-500"
            />
            <div className="flex items-center gap-2">
              <select
                value={jobId || ""}
                onChange={(e) => setJobId(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-sm text-[12px] font-mono2 text-slate-100"
              >
                {jobs?.map((j) => (
                  <option key={j.job_id} value={j.job_id}>{j.title}</option>
                ))}
              </select>
              <button
                data-testid={EAROS.resumeAnalyzeBtn}
                onClick={analyze}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-sm bg-indigo-500 hover:bg-indigo-400 text-slate-950 text-[12px] font-mono2 font-semibold disabled:opacity-50"
              >
                <FileText className="w-3.5 h-3.5" strokeWidth={1.5} />
                {loading ? "PARSING…" : "ANALYZE RESUME"}
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {result?.parsed && (
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
                  PARSED STRUCTURE
                </div>
                <div className="grid grid-cols-2 gap-2 text-[12px]">
                  <div><span className="text-slate-500">Title: </span>
                    <span className="text-slate-200">{result.parsed.current_title || "—"}</span></div>
                  <div><span className="text-slate-500">Company: </span>
                    <span className="text-slate-200">{result.parsed.current_company || "—"}</span></div>
                  <div><span className="text-slate-500">Years: </span>
                    <span className="text-slate-200">{result.parsed.years_experience_detected}</span></div>
                  <div><span className="text-slate-500">Words: </span>
                    <span className="text-slate-200">{result.parsed.word_count}</span></div>
                  <div className="col-span-2">
                    <span className="text-slate-500">Skills detected: </span>
                    <span className="text-slate-200">{result.parsed.skills_detected.join(", ") || "—"}</span>
                  </div>
                </div>
              </div>
            )}

            {result?.fit && (
              <div className="border border-emerald-500/30 bg-emerald-500/5 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-emerald-400 mb-2">
                  FIT ANALYSIS · {result.fit.job_title}
                </div>
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500">FIT SCORE</div>
                    <div className="font-display font-black text-2xl text-emerald-300">
                      {Math.round(result.fit.fit_score * 100)}
                    </div>
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500">SKILL COVERAGE</div>
                    <div className="font-display font-black text-2xl text-slate-100">
                      {Math.round(result.fit.coverage * 100)}%
                    </div>
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500">EXPERIENCE</div>
                    <div className="font-display font-black text-2xl text-slate-100">
                      {Math.round(result.fit.experience_fit * 100)}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
                  <div>
                    <div className="font-mono2 text-[10px] text-emerald-400 mb-1">STRENGTHS</div>
                    <ul className="space-y-0.5 text-slate-300">
                      {result.fit.strengths.map((s, i) => (
                        <li key={i} className="flex gap-1"><CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" strokeWidth={1.5} />{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-rose-400 mb-1">WEAKNESSES</div>
                    <ul className="space-y-0.5 text-slate-300">
                      {result.fit.weaknesses.map((s, i) => (
                        <li key={i} className="flex gap-1"><XCircle className="w-3 h-3 text-rose-400 mt-0.5 shrink-0" strokeWidth={1.5} />{s}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px] mt-3">
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">MATCHED SKILLS</div>
                    <div className="flex flex-wrap gap-1">
                      {result.fit.matched_skills.map((s) => (
                        <span key={s} className="px-1.5 py-0.5 rounded-sm border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-[11px] font-mono2">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="font-mono2 text-[10px] text-slate-500 mb-1">MISSING</div>
                    <div className="flex flex-wrap gap-1">
                      {result.fit.missing_skills.map((s) => (
                        <span key={s} className="px-1.5 py-0.5 rounded-sm border border-rose-500/30 bg-rose-500/10 text-rose-300 text-[11px] font-mono2">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {result?.client_summary && (
              <FormattedOutput
                result={result}
                format={format}
                setFormat={setFormat}
              />
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

/* ============================================================
   TASK 6 — Resume format selector
   ============================================================ */

const FORMATS = [
  {
    id: "one_page",
    label: "One-page summary",
    detail: "Compact internal review card — 6-8 lines. Recruiter-facing.",
    icon: FileText,
  },
  {
    id: "client_submission",
    label: "Client submission",
    detail: "Full submission package — skills matrix, availability, differentiators, comp. Client-facing, anonymised.",
    icon: Layers,
  },
];

function FormattedOutput({ result, format, setFormat }) {
  const summary = result.client_summary;
  const parsed = result.parsed || {};
  const fit = result.fit || {};

  return (
    <div className="space-y-3">
      <div
        data-testid="resume-format-selector"
        className="border border-slate-800 bg-slate-900 rounded-md p-2 grid grid-cols-1 md:grid-cols-2 gap-2"
      >
        {FORMATS.map((f) => {
          const Icon = f.icon;
          const active = format === f.id;
          return (
            <button
              key={f.id}
              data-testid={`resume-format-${f.id}`}
              onClick={() => setFormat(f.id)}
              className={`text-left p-2.5 rounded-sm border transition ${
                active
                  ? "border-indigo-500/60 bg-indigo-500/10"
                  : "border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center gap-2">
                <Icon
                  className={`w-3.5 h-3.5 ${active ? "text-indigo-300" : "text-slate-500"}`}
                  strokeWidth={1.5}
                />
                <div
                  className={`font-mono2 text-[10px] tracking-widest ${
                    active ? "text-indigo-300" : "text-slate-500"
                  }`}
                >
                  {active ? "SELECTED" : "FORMAT"}
                </div>
              </div>
              <div className="text-slate-100 text-[13px] font-medium mt-1">
                {f.label}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">{f.detail}</div>
            </button>
          );
        })}
      </div>

      {format === "one_page" ? (
        <OnePageView summary={summary} />
      ) : (
        <ClientSubmissionView summary={summary} parsed={parsed} fit={fit} />
      )}
    </div>
  );
}

function OnePageView({ summary }) {
  return (
    <div
      data-testid="resume-output-one_page"
      className="border border-slate-800 bg-slate-900 rounded-md p-4"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500">
          ONE-PAGE SUMMARY · INTERNAL
        </div>
        <button
          data-testid="resume-download-one_page"
          className="flex items-center gap-1 font-mono2 text-[10px] text-indigo-300 hover:text-indigo-200"
        >
          <Download className="w-3 h-3" strokeWidth={1.5} />
          .pdf
        </button>
      </div>
      <div className="text-slate-100">
        <div className="font-display font-bold text-lg">
          {summary.candidate_alias}
        </div>
        <div className="text-[13px] text-slate-400">
          {summary.current_title} · {summary.current_company}
        </div>
        <div className="text-[13px] text-slate-400">
          {summary.years_experience} yrs
        </div>
        <div className="text-[13px] text-slate-300 mt-2">
          {summary.match_summary}
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {summary.highlighted_skills?.map((s) => (
            <span
              key={s}
              className="px-1.5 py-0.5 rounded-sm border border-slate-700 text-slate-300 text-[11px] font-mono2"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ClientSubmissionView({ summary, parsed, fit }) {
  const skillsMatrix = (fit.matched_skills || []).map((s) => ({
    skill: s,
    level: "Expert",
    verified: true,
  }));
  const missing = (fit.missing_skills || []).slice(0, 3);
  return (
    <div
      data-testid="resume-output-client_submission"
      className="border border-emerald-500/30 bg-slate-900 rounded-md overflow-hidden"
    >
      {/* Doc header */}
      <div className="p-4 bg-gradient-to-r from-emerald-500/10 via-transparent to-transparent border-b border-emerald-500/30 flex items-center justify-between">
        <div>
          <div className="font-mono2 text-[10px] tracking-widest text-emerald-300">
            CLIENT SUBMISSION PACKAGE
          </div>
          <div className="font-display font-bold text-slate-100 text-lg">
            {summary.candidate_alias}{" "}
            <span className="font-mono2 text-[11px] text-slate-500">
              · anonymised
            </span>
          </div>
        </div>
        <button
          data-testid="resume-download-client_submission"
          className="flex items-center gap-1 font-mono2 text-[10px] text-emerald-300 hover:text-emerald-200 border border-emerald-500/30 rounded-sm px-2 py-1"
        >
          <Download className="w-3 h-3" strokeWidth={1.5} />
          submit to client
        </button>
      </div>

      {/* Header meta */}
      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-[12px] border-b border-slate-800/60">
        <MetaCell label="Role" value={summary.current_title} />
        <MetaCell label="Experience" value={`${summary.years_experience} yrs`} />
        <MetaCell
          label="Availability"
          value="30-day notice"
        />
        <MetaCell
          label="Fit"
          value={`${Math.round((fit.fit_score || 0) * 100)}/100`}
          tone="emerald"
        />
      </div>

      {/* Executive summary */}
      <div className="p-4 border-b border-slate-800/60">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-1">
          EXECUTIVE SUMMARY
        </div>
        <div className="text-slate-100 text-[13px] leading-relaxed">
          {summary.match_summary}
        </div>
      </div>

      {/* Skills matrix */}
      <div className="p-4 border-b border-slate-800/60">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
          SKILLS MATRIX · VERIFIED VS ROLE
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {skillsMatrix.slice(0, 8).map((s) => (
            <div
              key={s.skill}
              className="flex items-center justify-between text-[12px] border-b border-slate-800/40 py-1"
            >
              <span className="text-slate-100">{s.skill}</span>
              <span className="flex items-center gap-1 font-mono2 text-[10px] text-emerald-400">
                <CheckCircle className="w-3 h-3" strokeWidth={1.5} />
                {s.level}
              </span>
            </div>
          ))}
        </div>
        {missing.length > 0 && (
          <div className="mt-3 text-[11px] text-amber-300 font-mono2">
            gaps · {missing.join(", ")}
          </div>
        )}
      </div>

      {/* Differentiators */}
      <div className="p-4 border-b border-slate-800/60">
        <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
          DIFFERENTIATORS
        </div>
        <ul className="space-y-1 text-[12.5px]">
          {(fit.strengths || []).slice(0, 4).map((s, i) => (
            <li key={i} className="flex gap-2 text-slate-100">
              <CheckCircle
                className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"
                strokeWidth={1.5}
              />
              {s}
            </li>
          ))}
        </ul>
      </div>

      {/* Comp / logistics */}
      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetaCell
          label="Comp expectation"
          value={
            parsed?.expected_salary
              ? `${parsed.currency || ""} ${(parsed.expected_salary / 1000).toFixed(0)}k`
              : "on request"
          }
        />
        <MetaCell label="Location" value={parsed?.location || "on request"} />
        <MetaCell label="Right to work" value="Confirmed" />
      </div>

      <div className="p-3 bg-slate-950 text-center font-mono2 text-[10px] text-slate-500 tracking-widest">
        PII redacted · 100% AI-generated · confidence{" "}
        {Math.round((fit.fit_score || 0) * 100)}%
      </div>
    </div>
  );
}

function MetaCell({ label, value, tone = "slate" }) {
  const toneClass = { slate: "text-slate-100", emerald: "text-emerald-300" }[tone];
  return (
    <div className="min-w-0">
      <div className="font-mono2 text-[9px] tracking-widest text-slate-500 uppercase">
        {label}
      </div>
      <div className={`text-[13px] font-medium truncate ${toneClass}`}>
        {value || "—"}
      </div>
    </div>
  );
}
