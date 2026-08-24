import { describe, expect, it } from "vitest";
import { APPLICATION_REACTIVATION_GUARDRAILS, COLLABORATION_GUARDRAILS, HIRING_DECISION_GUARDRAILS, HIRING_PLAN_GUARDRAILS, OPERATIONAL_REQUISITION_GUARDRAILS, OFFER_GUARDRAILS, TABS, formatDate } from "./ATSOperations";
import { AUTONOMY_GUARDRAILS, WORKFLOW_DEFINITIONS } from "./ATSAutonomy";
import { CONTROL_PANELS, canManageEnterpriseControls } from "./EnterpriseControls";
import { CAREER_SITE_GUARDRAILS } from "./CareerSite";
import { CAREER_INTAKE_GUARDRAILS } from "@/components/CareerIntakeManager";
import { DATA_SUBJECT_GUARDRAILS } from "@/components/DataSubjectRequests";

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
      "offers",
      "handoffs",
    ]);
  });

  it("keeps the core recruiter tabs available for deterministic authenticated workflow validation", () => {
    expect(TABS.filter((tab) => ["candidates", "applications", "interviews", "offers"].includes(tab.key)).map((tab) => tab.key)).toEqual([
      "candidates",
      "applications",
      "interviews",
      "offers",
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

  it("keeps terminal application corrections separate from ordinary stage movement", () => {
    expect(APPLICATION_REACTIVATION_GUARDRAILS).toEqual([
      "terminal_hire_and_reject_outcomes_are_never_reversed_by_stage_move",
      "reactivation_requires_a_separate_independent_governance_approval",
      "approved_reactivation_appends_terminal_correction_provenance",
    ]);
  });

  it("keeps offer drafting record-only and distinct from final hiring approval", () => {
    expect(OFFER_GUARDRAILS).toEqual([
      "offer_creation_is_an_internal_draft_only",
      "drafting_never_sends_or_extends_an_offer",
      "final_hire_outcomes_require_independent_decision_approval",
    ]);
  });
  it("keeps hiring plans tenant-scoped and non-executing", () => {
    expect(HIRING_PLAN_GUARDRAILS).toEqual([
      "hiring_plan_is_tenant_scoped_within_the_requisition_record",
      "plan_captures_business_justification_budget_owner_and_target_dates",
      "planning_inputs_do_not_publish_or_change_candidate_status",
    ]);
  });

  it("keeps the operational requisition complete while retaining publication and candidate-contact controls", () => {
    expect(OPERATIONAL_REQUISITION_GUARDRAILS).toEqual([
      "requisition_captures_workforce_plan_and_job_definition",
      "compensation_and_process_design_remain_tenant_scoped",
      "creation_does_not_publish_or_contact_candidates",
    ]);
  });

  it("keeps autonomous ATS workflows bounded to reviewable, governed operations", () => {
    expect(WORKFLOW_DEFINITIONS.map((workflow) => workflow.capability)).toEqual([
      "cap.source_requisition_prospects",
      "cap.match_requisition",
      "cap.score_application",
      "cap.analyze_resume",
      "cap.draft_outreach",
      "cap.prepare_interview",
      "cap.prepare_job_publication",
      "cap.triage_requisition",
    ]);
  });

  it("keeps autonomous sourcing, resume review, and outreach within explicit consent, draft, and approval boundaries", () => {
    expect(AUTONOMY_GUARDRAILS).toEqual([
      "source_shortlists_require_active_recruiting_consent",
      "resume_analysis_uses_existing_parsed_profiles_only",
      "outreach_is_draft_only_and_never_provider_delivered",
      "plans_remain_policy_gated_and_auditable",
    ]);
  });

  it("keeps enterprise controls centered on reviewable compliance and administration work", () => {
    expect(CONTROL_PANELS).toEqual([
      "overview",
      "retention",
      "audit",
      "data-rights",
      "notifications",
      "administration",
      "integrations",
    ]);
  });

  it("keeps administrator-only control data behind an executable role gate", () => {
    expect(canManageEnterpriseControls({ role: "admin" })).toBe(true);
    expect(canManageEnterpriseControls({ role: "recruiter" })).toBe(false);
    expect(canManageEnterpriseControls({ role: "hiring_manager" })).toBe(false);
    expect(canManageEnterpriseControls(null)).toBe(false);
  });

  it("keeps public career-site intake consented, canonical, and free of outbound automation", () => {
    expect(CAREER_SITE_GUARDRAILS).toEqual([
      "only_enabled_open_requisitions_are_listed",
      "recruiting_consent_is_required_before_submission",
      "candidate_and_application_records_use_canonical_ats_models",
      "requisition_configured_questions_are_validated_and_stored_canonically",
      "candidate_withdrawal_requires_a_one_time_reference_and_preserves_application_provenance",
      "candidate_experience_feedback_requires_the_private_submission_reference_and_never_changes_hiring_state",
      "submission_never_triggers_outbound_automation",
    ]);
  });

  it("keeps career-site launch and referral intake explicitly enabled, attributable, and record-only", () => {
    expect(CAREER_INTAKE_GUARDRAILS).toEqual([
      "career_site_link_requires_published_and_enabled_requisition",
      "referral_submission_requires_explicit_intake_enablement",
      "referral_source_and_referrer_are_recorded_server_side",
      "intake_controls_do_not_trigger_outbound_automation",
    ]);
  });

  it("keeps data-subject requests tenant-scoped, reviewable, and retention-safe", () => {
    expect(DATA_SUBJECT_GUARDRAILS).toEqual([
      "requests_are_tenant_scoped_and_human_reviewed",
      "access_requests_link_to_auditable_export_manifests",
      "erasure_requests_require_policy_gated_retention_execution",
      "no_direct_candidate_data_mutation_from_request_intake",
    ]);
  });
});
