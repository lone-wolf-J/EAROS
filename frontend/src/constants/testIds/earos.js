// EAROS test IDs
export const EAROS = {
  // Layout
  sidebar: "earos-sidebar",
  topNav: "earos-topnav",
  navItem: (key) => `nav-item-${key}`,
  logoutBtn: "logout-btn",

  // Landing
  landingHero: "landing-hero",
  loginBtn: "login-google-btn",
  demoRecruiterBtn: "demo-login-recruiter-btn",
  demoManagerBtn: "demo-login-manager-btn",
  demoExecutiveBtn: "demo-login-executive-btn",

  // Dashboard
  dashboardRoot: "dashboard-root",
  kpiCard: (k) => `kpi-${k}`,
  pipelineStrip: "pipeline-strip",

  // Recruiter Copilot
  recruiterRoot: "recruiter-root",
  jobPicker: "job-picker",
  jobPickerItem: (id) => `job-picker-${id}`,
  candidateRow: (id) => `candidate-row-${id}`,
  aiDecisionCard: (id) => `ai-decision-${id}`,
  approveBtn: (id) => `approve-btn-${id}`,
  simulatePlanBtn: "simulate-plan-btn",
  planStepRow: (id) => `plan-step-${id}`,
  executePlanBtn: "execute-plan-btn",

  // Executive
  executiveRoot: "executive-root",
  strategyCard: "strategy-card",
  skillGapTable: "skill-gap-table",
  orgHealthTable: "org-health-table",

  // Candidate Assistant
  candidateAssistantRoot: "candidate-assistant-root",
  candidateIdInput: "candidate-id-input",
  candidateLookupBtn: "candidate-lookup-btn",

  // Governance
  governanceRoot: "governance-root",
  eventRow: (id) => `event-${id}`,
  approvalRow: (id) => `approval-${id}`,
  approvalGrantBtn: (id) => `approval-grant-${id}`,
  approvalDenyBtn: (id) => `approval-deny-${id}`,

  // Policy manager
  policyRoot: "policy-root",
  policyRow: (id) => `policy-${id}`,

  // World state explorer
  worldRoot: "world-state-root",
  worldTab: (key) => `world-tab-${key}`,

  // Capability registry
  capabilityRoot: "capability-root",
  capabilityRow: (id) => `capability-${id}`,

  // Planner viewer
  plannerRoot: "planner-root",
  plannerGoalInput: "planner-goal-input",
  plannerContextInput: "planner-context-input",
  plannerRunBtn: "planner-run-btn",

  // Reflection
  reflectionRoot: "reflection-root",
  reflectionRow: (id) => `reflection-${id}`,
};
