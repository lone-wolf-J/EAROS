import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = location.hash || window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      navigate("/", { replace: true });
      return;
    }
    const sessionId = decodeURIComponent(match[1]);
    (async () => {
      try {
        await api.post("/auth/session", null, {
          headers: { "X-Session-ID": sessionId },
        });
        await checkAuth();
        // Clean the URL fragment then redirect
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { replace: true });
      } catch {
        navigate("/", { replace: true });
      }
    })();
  }, [location.hash, navigate, checkAuth]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center font-mono text-sm">
      <span className="animate-pulse">Establishing secure session…</span>
    </div>
  );
}
