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
const Landing = React.lazy(() => import("@/pages/Landing"));
const AuthCallback = React.lazy(() => import("@/pages/AuthCallback"));
const MissionControl = React.lazy(() => import("@/pages/MissionControl"));
const Scenarios = React.lazy(() => import("@/pages/Scenarios"));
const HiringIntake = React.lazy(() => import("@/pages/HiringIntake"));
const HiringDashboard = React.lazy(() => import("@/pages/HiringDashboard"));
const RecruiterCopilot = React.lazy(() => import("@/pages/RecruiterCopilot"));
const ExecutiveCopilot = React.lazy(() => import("@/pages/ExecutiveCopilot"));
const CandidateAssistant = React.lazy(() => import("@/pages/CandidateAssistant"));
const Governance = React.lazy(() => import("@/pages/Governance"));
const PolicyManager = React.lazy(() => import("@/pages/PolicyManager"));
const CapabilityRegistry = React.lazy(() => import("@/pages/CapabilityRegistry"));
const WorldStateExplorer = React.lazy(() => import("@/pages/WorldStateExplorer"));
const PlannerView = React.lazy(() => import("@/pages/PlannerView"));
const ReflectionReports = React.lazy(() => import("@/pages/ReflectionReports"));
const Agents = React.lazy(() => import("@/pages/Agents"));
const Integrations = React.lazy(() => import("@/pages/Integrations"));
const Sourcing = React.lazy(() => import("@/pages/Sourcing"));
const ResumeStudio = React.lazy(() => import("@/pages/ResumeStudio"));
const OutreachStudio = React.lazy(() => import("@/pages/OutreachStudio"));
const Screening = React.lazy(() => import("@/pages/Screening"));
const VoiceInterview = React.lazy(() => import("@/pages/VoiceInterview"));
const InterviewSuite = React.lazy(() => import("@/pages/InterviewSuite"));
const DeepDive = React.lazy(() => import("@/pages/DeepDive"));
const ATSOperations = React.lazy(() => import("@/pages/ATSOperations"));
const ATSAutonomy = React.lazy(() => import("@/pages/ATSAutonomy"));
const EnterpriseControls = React.lazy(() => import("@/pages/EnterpriseControls"));
const CareerSite = React.lazy(() => import("@/pages/CareerSite"));

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
  ["/ats", ATSOperations],
  ["/ats/workflows", ATSAutonomy],
  ["/enterprise-controls", EnterpriseControls],
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
    <React.Suspense fallback={<div className="min-h-screen bg-slate-950 text-slate-500 flex items-center justify-center font-mono text-sm"><span className="animate-pulse">Loading EAROS workspace…</span></div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/careers" element={<CareerSite />} />
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
    </React.Suspense>
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
