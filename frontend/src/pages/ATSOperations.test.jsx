import { describe, expect, it } from "vitest";
import { COLLABORATION_GUARDRAILS, HIRING_DECISION_GUARDRAILS, TABS, formatDate } from "./ATSOperations";
import { WORKFLOW_DEFINITIONS } from "./ATSAutonomy";
import { CONTROL_PANELS, canManageEnterpriseControls } from "./EnterpriseControls";

describe("ATS Operations route contract", () => {
  it("keeps the enterprise records workbench focused on core ATS workstreams", () => {
    expect(TABS.map((tab) => tab.key)).toEqual([
      "requisitions",
      "candidates",
      "applications",
      "pools",
      "interviews",
      "collaboration",
      "distribution",
      "handoffs",
    ]);
  });

  it("renders an explicit empty date placeholder rather than leaking invalid values", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("keeps team mentions, communications, and candidate notices under explicit recruiter guardrails", () => {
    expect(COLLABORATION_GUARDRAILS).toEqual([
      "mentions_validate_tenant_users",
      "communications_are_recorded_not_delivered",
      "candidate_notifications_are_recorded_not_delivered",
      "outbound_email_and_sms_require_active_recruiting_consent",
    ]);
  });

  it("keeps final hiring outcomes approval-gated and independently reviewable", () => {
    expect(HIRING_DECISION_GUARDRAILS).toEqual([
      "final_outcomes_enter_governance_approval_queue",
      "requester_cannot_approve_or_deny_own_decision",
      "application_status_changes_only_after_independent_grant",
    ]);
  });

  it("keeps autonomous ATS workflows bounded to reviewable, governed operations", () => {
    expect(WORKFLOW_DEFINITIONS.map((workflow) => workflow.capability)).toEqual([
      "cap.match_requisition",
      "cap.score_application",
      "cap.prepare_interview",
      "cap.prepare_job_publication",
      "cap.triage_requisition",
    ]);
  });

  it("keeps enterprise controls centered on reviewable compliance and administration work", () => {
    expect(CONTROL_PANELS).toEqual([
      "overview",
      "retention",
      "audit",
      "notifications",
      "administration",
    ]);
  });

  it("keeps administrator-only control data behind an executable role gate", () => {
    expect(canManageEnterpriseControls({ role: "admin" })).toBe(true);
    expect(canManageEnterpriseControls({ role: "recruiter" })).toBe(false);
    expect(canManageEnterpriseControls({ role: "hiring_manager" })).toBe(false);
    expect(canManageEnterpriseControls(null)).toBe(false);
  });
});
