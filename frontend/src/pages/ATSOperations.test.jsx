import { describe, expect, it } from "vitest";
import { TABS, formatDate } from "./ATSOperations";
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
