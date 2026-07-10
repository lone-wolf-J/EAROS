"""World State — single source of truth.

Contains Organizations, Departments, Teams, Requisitions (Jobs), Candidates,
Offers, Skills, Policies, Pipelines, and current execution state.

Planner always reasons AGAINST World State (never against LLM memory alone).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    JobStatus,
    OfferStatus,
    PipelineStage,
    Sensitivity,
    new_candidate_id,
    new_department_id,
    new_job_id,
    new_offer_id,
    new_organization_id,
    new_skill_id,
    new_team_id,
    utcnow_iso,
)


# ---------- Documents ----------

class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organization_id: str = Field(default_factory=new_organization_id)
    name: str
    domain: str
    industry: str
    headquarters: str
    hq_country: str
    total_headcount: int = 0
    active_reqs: int = 0
    created_at: str = Field(default_factory=utcnow_iso)


class Department(BaseModel):
    model_config = ConfigDict(extra="ignore")
    department_id: str = Field(default_factory=new_department_id)
    organization_id: str
    name: str
    leader_name: str
    headcount: int = 0
    attrition_rate: float = 0.0
    health_score: float = 0.75


class Team(BaseModel):
    model_config = ConfigDict(extra="ignore")
    team_id: str = Field(default_factory=new_team_id)
    department_id: str
    organization_id: str
    name: str
    manager_name: str
    headcount: int = 0
    open_seats: int = 0


class Skill(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill_id: str = Field(default_factory=new_skill_id)
    name: str
    category: str  # technical | functional | leadership | domain
    market_scarcity: float = 0.5  # 0..1 higher = scarcer


class Job(BaseModel):
    """Open requisition."""
    model_config = ConfigDict(extra="ignore")
    job_id: str = Field(default_factory=new_job_id)
    organization_id: str
    department_id: str
    team_id: Optional[str] = None
    title: str
    level: str  # IC3, IC4, IC5, M4, M5, VP
    location: str
    country: str  # India | USA
    employment_type: str = "Full-time"
    salary_min: int
    salary_max: int
    currency: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    priority: str = "P2"  # P0 P1 P2 P3
    business_impact: str
    status: JobStatus = JobStatus.OPEN
    hiring_manager: str
    opened_days_ago: int = 0
    target_close_days: int = 45
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    created_at: str = Field(default_factory=utcnow_iso)


class Candidate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate_id: str = Field(default_factory=new_candidate_id)
    organization_id: str
    job_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    location: str
    country: str
    current_title: str
    current_company: str
    years_experience: float
    expected_salary: int
    currency: str
    skills: list[str] = Field(default_factory=list)
    stage: PipelineStage = PipelineStage.SOURCED
    source: str = "sourced"  # sourced | applied | referral | agency
    fit_score: float = 0.0  # populated by intelligence
    risk_flags: list[str] = Field(default_factory=list)
    picture: Optional[str] = None
    notes: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utcnow_iso)


class Offer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    offer_id: str = Field(default_factory=new_offer_id)
    organization_id: str
    candidate_id: str
    job_id: str
    base_salary: int
    bonus: int = 0
    equity_units: int = 0
    signing_bonus: int = 0
    currency: str
    status: OfferStatus = OfferStatus.DRAFT
    acceptance_probability: float = 0.0
    market_percentile: float = 0.0
    internal_parity_delta: float = 0.0
    reasoning_decision_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


# ---------- Repository ----------

class WorldState:
    """Repository facade over MongoDB. All queries exclude _id."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # organization
    async def upsert_organization(self, org: Organization) -> Organization:
        await self.db.organizations.update_one(
            {"organization_id": org.organization_id}, {"$set": org.model_dump()}, upsert=True
        )
        return org

    async def get_organization(self, organization_id: str) -> Optional[Organization]:
        doc = await self.db.organizations.find_one({"organization_id": organization_id}, {"_id": 0})
        return Organization(**doc) if doc else None

    async def list_organizations(self) -> list[Organization]:
        docs = await self.db.organizations.find({}, {"_id": 0}).to_list(100)
        return [Organization(**d) for d in docs]

    # departments / teams
    async def upsert_department(self, d: Department) -> Department:
        await self.db.departments.update_one(
            {"department_id": d.department_id}, {"$set": d.model_dump()}, upsert=True
        )
        return d

    async def list_departments(self, organization_id: str) -> list[Department]:
        docs = await self.db.departments.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Department(**d) for d in docs]

    async def upsert_team(self, t: Team) -> Team:
        await self.db.teams.update_one(
            {"team_id": t.team_id}, {"$set": t.model_dump()}, upsert=True
        )
        return t

    async def list_teams(self, organization_id: str) -> list[Team]:
        docs = await self.db.teams.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Team(**d) for d in docs]

    # skills
    async def upsert_skill(self, s: Skill) -> Skill:
        await self.db.skills.update_one(
            {"skill_id": s.skill_id}, {"$set": s.model_dump()}, upsert=True
        )
        return s

    async def list_skills(self) -> list[Skill]:
        docs = await self.db.skills.find({}, {"_id": 0}).to_list(1000)
        return [Skill(**d) for d in docs]

    # jobs
    async def upsert_job(self, j: Job) -> Job:
        await self.db.jobs.update_one(
            {"job_id": j.job_id}, {"$set": j.model_dump()}, upsert=True
        )
        return j

    async def get_job(self, job_id: str) -> Optional[Job]:
        doc = await self.db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        return Job(**doc) if doc else None

    async def list_jobs(self, organization_id: str, status: Optional[JobStatus] = None) -> list[Job]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if status:
            q["status"] = status.value
        docs = await self.db.jobs.find(q, {"_id": 0}).to_list(500)
        return [Job(**d) for d in docs]

    # candidates
    async def upsert_candidate(self, c: Candidate) -> Candidate:
        await self.db.candidates.update_one(
            {"candidate_id": c.candidate_id}, {"$set": c.model_dump()}, upsert=True
        )
        return c

    async def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        doc = await self.db.candidates.find_one({"candidate_id": candidate_id}, {"_id": 0})
        return Candidate(**doc) if doc else None

    async def list_candidates(
        self,
        organization_id: str,
        job_id: Optional[str] = None,
        stage: Optional[PipelineStage] = None,
    ) -> list[Candidate]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if job_id:
            q["job_id"] = job_id
        if stage:
            q["stage"] = stage.value
        docs = await self.db.candidates.find(q, {"_id": 0}).to_list(2000)
        return [Candidate(**d) for d in docs]

    async def set_candidate_stage(self, candidate_id: str, stage: PipelineStage) -> None:
        await self.db.candidates.update_one(
            {"candidate_id": candidate_id}, {"$set": {"stage": stage.value}}
        )

    async def add_candidate_note(self, candidate_id: str, note: dict[str, Any]) -> None:
        await self.db.candidates.update_one(
            {"candidate_id": candidate_id}, {"$push": {"notes": note}}
        )

    # offers
    async def upsert_offer(self, o: Offer) -> Offer:
        await self.db.offers.update_one(
            {"offer_id": o.offer_id}, {"$set": o.model_dump()}, upsert=True
        )
        return o

    async def list_offers(self, organization_id: str) -> list[Offer]:
        docs = await self.db.offers.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Offer(**d) for d in docs]
