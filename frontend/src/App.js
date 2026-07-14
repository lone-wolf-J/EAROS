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
import MissionControl from "@/pages/MissionControl";
import Scenarios from "@/pages/Scenarios";
import HiringIntake from "@/pages/HiringIntake";
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
import Agents from "@/pages/Agents";
import Integrations from "@/pages/Integrations";
import Sourcing from "@/pages/Sourcing";
import ResumeStudio from "@/pages/ResumeStudio";
import OutreachStudio from "@/pages/OutreachStudio";
import Screening from "@/pages/Screening";
import VoiceInterview from "@/pages/VoiceInterview";
import InterviewSuite from "@/pages/InterviewSuite";
import DeepDive from "@/pages/DeepDive";

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

const ROUTES = [
  ["/mission", MissionControl],
  ["/scenarios", Scenarios],
  ["/intake", HiringIntake],
  ["/dashboard", HiringDashboard],
  ["/recruiter", RecruiterCopilot],
  ["/sourcing", Sourcing],
  ["/resume", ResumeStudio],
  ["/outreach", OutreachStudio],
  ["/screening", Screening],
  ["/voice", VoiceInterview],
  ["/interview", InterviewSuite],
  ["/executive", ExecutiveCopilot],
  ["/candidate", CandidateAssistant],
  ["/planner", PlannerView],
  ["/deep-dive", DeepDive],
  ["/agents", Agents],
  ["/integrations", Integrations],
  ["/world", WorldStateExplorer],
  ["/capabilities", CapabilityRegistry],
  ["/policies", PolicyManager],
  ["/governance", Governance],
  ["/reflection", ReflectionReports],
];

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      {ROUTES.map(([path, Comp]) => (
        <Route
          key={path}
          path={path}
          element={
            <Protected>
              <Comp />
            </Protected>
          }
        />
      ))}
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
