import React from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import "@/App.css";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Landing from "@/pages/Landing";
import AuthCallback from "@/pages/AuthCallback";
import HiringDashboard from "@/pages/HiringDashboard";
import RecruiterCopilot from "@/pages/RecruiterCopilot";
import ExecutiveCopilot from "@/pages/ExecutiveCopilot";
import CandidateAssistant from "@/pages/CandidateAssistant";
import Governance from "@/pages/Governance";
import PolicyManager from "@/pages/PolicyManager";
import CapabilityRegistry from "@/pages/CapabilityRegistry";
import WorldStateExplorer from "@/pages/WorldStateExplorer";
import PlannerView from "@/pages/PlannerView";
import ReflectionReports from "@/pages/ReflectionReports";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-500 flex items-center justify-center font-mono text-sm">
        <span className="animate-pulse">Verifying session…</span>
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  // Detect OAuth callback synchronously — the URL fragment contains session_id
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <HiringDashboard />
          </Protected>
        }
      />
      <Route
        path="/recruiter"
        element={
          <Protected>
            <RecruiterCopilot />
          </Protected>
        }
      />
      <Route
        path="/executive"
        element={
          <Protected>
            <ExecutiveCopilot />
          </Protected>
        }
      />
      <Route
        path="/candidate"
        element={
          <Protected>
            <CandidateAssistant />
          </Protected>
        }
      />
      <Route
        path="/planner"
        element={
          <Protected>
            <PlannerView />
          </Protected>
        }
      />
      <Route
        path="/world"
        element={
          <Protected>
            <WorldStateExplorer />
          </Protected>
        }
      />
      <Route
        path="/capabilities"
        element={
          <Protected>
            <CapabilityRegistry />
          </Protected>
        }
      />
      <Route
        path="/policies"
        element={
          <Protected>
            <PolicyManager />
          </Protected>
        }
      />
      <Route
        path="/governance"
        element={
          <Protected>
            <Governance />
          </Protected>
        }
      />
      <Route
        path="/reflection"
        element={
          <Protected>
            <ReflectionReports />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
