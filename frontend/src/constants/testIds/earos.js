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

  // Mission Control
  missionRoot: "mission-root",
  missionKpi: (k) => `mission-kpi-${k}`,
  agentPulseCard: (id) => `agent-pulse-${id}`,
  ambientTicker: "ambient-ticker",
  runningExecutionCard: (id) => `running-exec-${id}`,
  approvalMission: (id) => `mission-approval-${id}`,

  // Scenarios
  scenariosRoot: "scenarios-root",
  scenarioCard: (id) => `scenario-${id}`,
  scenarioRunBtn: (id) => `scenario-run-${id}`,

  // Orchestration
  orchestrationRoot: "orchestration-root",
  orchestrationNode: (key) => `orch-node-${key}`,

  // Intake
  intakeRoot: "intake-root",
  intakeBriefInput: "intake-brief-input",
  intakeRunBtn: "intake-run-btn",
  intakeExamples: "intake-examples",

  // Agents / Integrations
  agentsRoot: "agents-root",
  agentCard: (id) => `agent-card-${id}`,
  integrationsRoot: "integrations-root",
  integrationCard: (id) => `integration-card-${id}`,

  // Sourcing / Resume / Outreach / Screening / Voice
  sourcingRoot: "sourcing-root",
  sourcingRunBtn: "sourcing-run-btn",
  resumeRoot: "resume-root",
  resumeAnalyzeBtn: "resume-analyze-btn",
  outreachRoot: "outreach-root",
  screeningRoot: "screening-root",
  voiceRoot: "voice-root",
  voiceStartBtn: "voice-start-btn",
  voiceNextBtn: "voice-next-btn",
  voiceSummarizeBtn: "voice-summarize-btn",

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
  simulateAttritionSlider: "sim-attrition",
  simulateHiringFreeze: "sim-freeze",
  simulateBudget: "sim-budget",
  simulateBangalore: "sim-bang",
  simulateAiDoubles: "sim-ai",

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
  policySimulateBtn: "policy-simulate-btn",

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
