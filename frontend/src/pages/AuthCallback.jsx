import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState(null);
  const [phase, setPhase] = useState("reading fragment…");

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = location.hash || window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      setError({
        code: "NO_SESSION_ID",
        message: "No session_id fragment was returned by Emergent OAuth.",
        detail: `Current hash: ${hash || "(empty)"}`,
      });
      return;
    }
    const sessionId = decodeURIComponent(match[1]);
    (async () => {
      try {
        setPhase("exchanging session with backend…");
        await api.post("/auth/session", null, {
          headers: { "X-Session-ID": sessionId },
        });
        setPhase("verifying session…");
        await checkAuth();
        setPhase("done");
        window.history.replaceState(null, "", "/mission");
        navigate("/mission", { replace: true });
      } catch (e) {
        setError({
          code: e.response?.status || "NETWORK",
          message:
            e.response?.data?.detail ||
            e.message ||
            "Unknown error while creating the session.",
          detail: `POST /api/auth/session · ${
            e.response?.status || "no-response"
          } · session_id length ${sessionId.length}`,
        });
      }
    })();
  }, [location.hash, navigate, checkAuth]);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <div className="max-w-lg w-full border border-rose-500/40 bg-rose-500/5 rounded-md p-6">
          <div className="font-mono2 text-[10px] tracking-widest text-rose-400 mb-2">
            SIGN-IN FAILED · {error.code}
          </div>
          <h2 className="font-display text-xl font-bold text-slate-100 mb-2">
            EAROS couldn&apos;t establish your session.
          </h2>
          <div className="text-slate-300 text-[13px] mb-3">{error.message}</div>
          <pre className="font-mono2 text-[11px] text-slate-500 bg-slate-950 border border-slate-800 rounded-sm p-3 whitespace-pre-wrap">
            {error.detail}
          </pre>
          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={() => navigate("/", { replace: true })}
              className="px-3 py-2 rounded-sm border border-slate-800 hover:border-slate-700 text-slate-300 text-[12px] font-mono2"
            >
              back to landing
            </button>
            <button
              onClick={() => {
                hasProcessed.current = false;
                setError(null);
                setPhase("retrying…");
                window.location.reload();
              }}
              className="px-3 py-2 rounded-sm bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[12px] font-mono2"
            >
              retry
            </button>
          </div>
          <div className="mt-4 text-[11px] text-slate-500">
            Tip: if you keep seeing this, try the &ldquo;DEMO ROLES&rdquo; buttons on the
            landing page — they don&apos;t use Google OAuth.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center font-mono text-sm">
      <span className="animate-pulse">{phase}</span>
    </div>
  );
}
