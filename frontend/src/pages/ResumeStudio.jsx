import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { CheckCircle, FileText, ScrollText, XCircle } from "lucide-react";
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
              <div className="border border-slate-800 bg-slate-900 rounded-md p-4">
                <div className="font-mono2 text-[10px] tracking-widest text-slate-500 mb-2">
                  CLIENT-READY ONE-PAGER
                </div>
                <div className="text-slate-100">
                  <div className="font-display font-bold text-lg">
                    {result.client_summary.candidate_alias}
                  </div>
                  <div className="text-[13px] text-slate-400">
                    {result.client_summary.current_title} · {result.client_summary.current_company}
                  </div>
                  <div className="text-[13px] text-slate-400">
                    {result.client_summary.years_experience} yrs
                  </div>
                  <div className="text-[13px] text-slate-300 mt-2">
                    {result.client_summary.match_summary}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {result.client_summary.highlighted_skills?.map((s) => (
                      <span key={s} className="px-1.5 py-0.5 rounded-sm border border-slate-700 text-slate-300 text-[11px] font-mono2">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
