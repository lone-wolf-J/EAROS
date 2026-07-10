"""External integrations catalog (mocked connection state).

Represents the systems EAROS *would* connect to in production: ATS/CRM,
job boards, communication tools, and social/professional sources. The
frontend shows connection status, last sync, records available, permissions.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field


class IntegrationSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    integration_id: str
    name: str
    category: str  # ats | crm | job_board | social | communication | referral | community
    color: str  # brand color
    connection_status: str  # connected | degraded | rate_limited | disconnected
    health: str  # healthy | warning | error
    last_sync: str
    records_available: int
    permissions: list[str]
    latency_ms: int
    coverage_geo: list[str]


def _sync_ago(seed: str, max_min: int = 90) -> str:
    r = random.Random(seed)
    dt = datetime.now(timezone.utc) - timedelta(minutes=r.randint(1, max_min))
    return dt.isoformat()


def _mk(integration_id: str, name: str, category: str, color: str,
        records: int, geo: list[str],
        status: str = "connected", health: str = "healthy",
        latency_ms: int = 220,
        permissions: list[str] = None) -> IntegrationSpec:
    return IntegrationSpec(
        integration_id=integration_id, name=name, category=category, color=color,
        connection_status=status, health=health,
        last_sync=_sync_ago(integration_id),
        records_available=records, coverage_geo=geo,
        latency_ms=latency_ms,
        permissions=permissions or ["read:candidates", "read:jobs"],
    )


INTEGRATIONS: list[IntegrationSpec] = [
    # ATS / CRM
    _mk("int.ceipal", "CEIPAL", "ats", "#0ea5e9", 12483, ["US", "India"]),
    _mk("int.bullhorn", "Bullhorn", "ats", "#f97316", 8942, ["US", "UK"]),
    _mk("int.greenhouse", "Greenhouse", "ats", "#25a768", 4520, ["US"]),
    _mk("int.lever", "Lever", "ats", "#6366f1", 3105, ["US"]),
    _mk("int.recruiter_com", "Recruiter.com", "ats", "#8b5cf6", 2210, ["US"], status="degraded", health="warning", latency_ms=1200),
    _mk("int.internal_ats", "LevelShift Internal ATS", "ats", "#10b981", 15200, ["US", "India"], latency_ms=90),
    # Job Boards
    _mk("int.linkedin", "LinkedIn Recruiter", "job_board", "#0a66c2", 82000, ["Global"], permissions=["read:profiles", "send:inmail"]),
    _mk("int.dice", "Dice", "job_board", "#c62828", 18400, ["US"], permissions=["read:candidates", "post:jobs"]),
    _mk("int.monster", "Monster", "job_board", "#7b2cbf", 12100, ["US", "UK", "India"]),
    _mk("int.indeed", "Indeed", "job_board", "#003a9b", 45300, ["Global"]),
    _mk("int.naukri", "Naukri", "job_board", "#4a154b", 68000, ["India"]),
    _mk("int.ziprecruiter", "ZipRecruiter", "job_board", "#22c55e", 22100, ["US"]),
    _mk("int.wellfound", "Wellfound", "job_board", "#0f172a", 3400, ["US"]),
    # Social / Developer
    _mk("int.github", "GitHub", "social", "#8b5cf6", 12000, ["Global"], permissions=["read:public_profile", "read:repos"]),
    _mk("int.stackoverflow", "Stack Overflow", "social", "#f48024", 6800, ["Global"], status="rate_limited", health="warning", latency_ms=800),
    # Communication
    _mk("int.gmail", "Gmail / Outlook", "communication", "#ea4335", 0, ["Global"], permissions=["send:mail", "watch:inbox"]),
    _mk("int.slack", "Slack", "communication", "#611f69", 0, ["Global"], permissions=["send:messages"]),
    _mk("int.teams", "Microsoft Teams", "communication", "#4b53bc", 0, ["Global"], permissions=["send:messages"]),
    _mk("int.whatsapp", "WhatsApp Business", "communication", "#25d366", 0, ["Global"], permissions=["send:messages"]),
    _mk("int.twilio_sms", "Twilio SMS", "communication", "#f22f46", 0, ["Global"], permissions=["send:sms"]),
    # Referral / Community
    _mk("int.referrals", "Referral Database", "referral", "#f59e0b", 4100, ["US", "India"], permissions=["read:employees", "read:referrals"]),
    _mk("int.community", "LevelShift Talent Community", "community", "#84cc16", 9200, ["US", "India"]),
    _mk("int.hrms_workday", "Workday HRMS", "crm", "#ff6b00", 237, ["US", "India"], permissions=["read:employees"]),
    _mk("int.calendar", "Google Calendar", "communication", "#4285f4", 0, ["Global"], permissions=["read:events", "write:events"]),
]


def list_integrations() -> list[IntegrationSpec]:
    return INTEGRATIONS
