"""Seed the World State with LevelShift demo data.

Idempotent — safe to run on every boot. Also seeds demo users and default policies.
"""
from __future__ import annotations

import random
from typing import Any


def _derive_candidate_title(job_title: str, rng: random.Random) -> str:
    """Produce a sensible candidate current-title from the job title without
    ever duplicating the seniority word (e.g. 'Senior Senior Engineer')."""
    base = job_title.replace("Lead ", "").replace("Principal ", "Sr. ")
    if rng.random() < 0.6:
        return base
    # Strip any leading seniority word from the domain so 'Senior <domain>
    # Engineer' never reads 'Senior Senior Engineer'.
    first = job_title.split()[0]
    if first.lower() in {"senior", "sr.", "sr", "principal", "staff", "lead"}:
        # Skip the seniority word — take the domain word after it if present
        parts = job_title.split()
        domain = parts[1] if len(parts) > 1 else "Software"
    else:
        domain = first
    if domain.lower() == "engineer":
        domain = "Software"
    return f"Senior {domain} Engineer"



from motor.motor_asyncio import AsyncIOMotorDatabase

from foundation import (
    JobStatus,
    PipelineStage,
    Sensitivity,
    new_department_id,
    new_team_id,
    new_user_id,
    utcnow_iso,
)
from platform_core.policy import Policy
from platform_core.world import (
    Candidate,
    Department,
    Job,
    Organization,
    Skill,
    Team,
    WorldState,
)

ORG_ID = "org_levelshift"

DEPARTMENTS = [
    ("dept_platform", "Platform & AI", "Aditi Sharma", 62, 0.09, 0.82),
    ("dept_data", "Data Engineering", "Rohan Iyer", 44, 0.11, 0.78),
    ("dept_crm", "CRM Practice (Salesforce & Dynamics)", "Meera Krishnan", 71, 0.14, 0.71),
    ("dept_sales", "Sales & GTM", "James Patterson", 38, 0.18, 0.68),
    ("dept_success", "Client Partnerships", "Priya Menon", 22, 0.07, 0.86),
]

TEAMS = [
    ("team_ai_core", "dept_platform", "AI Core", "Vikram Reddy", 12, 3),
    ("team_ml_platform", "dept_platform", "ML Platform", "Sarah Lin", 9, 2),
    ("team_de_ingest", "dept_data", "Data Ingestion", "Kabir Nair", 8, 2),
    ("team_de_lakehouse", "dept_data", "Lakehouse", "Anita George", 7, 1),
    ("team_sfdc", "dept_crm", "Salesforce Delivery", "Rahul Menon", 18, 4),
    ("team_dynamics", "dept_crm", "Dynamics 365 Delivery", "Neha Kapoor", 14, 3),
    ("team_sales_us", "dept_sales", "Enterprise Sales — Americas", "David Cohen", 12, 2),
    ("team_sales_in", "dept_sales", "Enterprise Sales — India", "Ishaan Bhatt", 8, 2),
    ("team_cp", "dept_success", "Client Partners", "Elena Rodriguez", 10, 3),
]

SKILLS = [
    "Salesforce Apex", "Salesforce LWC", "Salesforce CPQ", "Salesforce Marketing Cloud",
    "Dynamics 365 CE", "Dynamics 365 F&O", "Power Platform", "Power Automate",
    "Python", "PySpark", "Airflow", "dbt", "Snowflake", "Databricks",
    "PyTorch", "LangChain", "LangGraph", "RAG", "LLM Ops", "Vector DBs",
    "Kafka", "Kubernetes", "AWS", "Azure", "Terraform",
    "Enterprise Sales", "MEDDIC", "Value Selling", "Account Planning",
    "Client Partnership", "Program Delivery", "Stakeholder Management",
]

JOB_TEMPLATES: list[dict[str, Any]] = [
    dict(job_id="job_sfdc_lead_bangalore", title="Salesforce Lead Engineer",
         team_id="team_sfdc", department_id="dept_crm", level="IC5",
         location="Bangalore, India", country="India",
         salary_min=2800000, salary_max=4200000, currency="INR", priority="P0",
         business_impact="Delivery lead for TalentIQ client; slips risk USD 1.4M ARR.",
         required_skills=["Salesforce Apex", "Salesforce LWC", "Salesforce CPQ"],
         nice_to_have=["Salesforce Marketing Cloud", "MuleSoft"],
         hiring_manager="Rahul Menon"),
    dict(job_id="job_sfdc_arch_austin", title="Salesforce Architect",
         team_id="team_sfdc", department_id="dept_crm", level="M4",
         location="Austin, USA", country="USA",
         salary_min=175000, salary_max=225000, currency="USD", priority="P0",
         business_impact="Anchor architect for Americas SFDC book; unlocks 3 new logos.",
         required_skills=["Salesforce Apex", "Salesforce CPQ", "Salesforce LWC"],
         nice_to_have=["MuleSoft", "Heroku"],
         hiring_manager="Elena Rodriguez"),
    dict(job_id="job_dyn_cons_hyd", title="Dynamics 365 F&O Consultant",
         team_id="team_dynamics", department_id="dept_crm", level="IC4",
         location="Hyderabad, India", country="India",
         salary_min=1800000, salary_max=2800000, currency="INR", priority="P1",
         business_impact="Scale D365 F&O practice ahead of Q2 pipeline.",
         required_skills=["Dynamics 365 F&O", "Power Platform"],
         nice_to_have=["Azure", "Power Automate"],
         hiring_manager="Neha Kapoor"),
    dict(job_id="job_dyn_lead_nyc", title="Dynamics 365 CE Practice Lead",
         team_id="team_dynamics", department_id="dept_crm", level="M4",
         location="New York, USA", country="USA",
         salary_min=185000, salary_max=235000, currency="USD", priority="P1",
         business_impact="Lead D365 CE growth in Americas — key differentiator vs. big 4.",
         required_skills=["Dynamics 365 CE", "Power Platform", "Program Delivery"],
         nice_to_have=["Azure"],
         hiring_manager="Meera Krishnan"),
    dict(job_id="job_ai_staff_bang", title="Staff AI Engineer (Agentic Systems)",
         team_id="team_ai_core", department_id="dept_platform", level="IC5",
         location="Bangalore, India", country="India",
         salary_min=4500000, salary_max=6500000, currency="INR", priority="P0",
         business_impact="Core builder for EAROS Intelligence — direct product moat.",
         required_skills=["Python", "PyTorch", "LangGraph", "RAG"],
         nice_to_have=["LLM Ops", "Vector DBs"],
         hiring_manager="Vikram Reddy"),
    dict(job_id="job_ai_pm_sf", title="Principal AI Product Manager",
         team_id="team_ai_core", department_id="dept_platform", level="M5",
         location="San Francisco, USA", country="USA",
         salary_min=210000, salary_max=280000, currency="USD", priority="P0",
         business_impact="Own EAROS Intelligence product line — sets 12-month roadmap.",
         required_skills=["LLM Ops", "RAG", "Stakeholder Management"],
         nice_to_have=["LangChain"],
         hiring_manager="Aditi Sharma"),
    dict(job_id="job_de_lead_pune", title="Data Engineering Lead (Lakehouse)",
         team_id="team_de_lakehouse", department_id="dept_data", level="IC5",
         location="Pune, India", country="India",
         salary_min=3200000, salary_max=4500000, currency="INR", priority="P1",
         business_impact="Own governed lakehouse — feeds Executive Copilot forecasts.",
         required_skills=["Databricks", "PySpark", "dbt"],
         nice_to_have=["Kafka", "Airflow"],
         hiring_manager="Anita George"),
    dict(job_id="job_de_ing_sea", title="Senior Data Engineer",
         team_id="team_de_ingest", department_id="dept_data", level="IC4",
         location="Seattle, USA", country="USA",
         salary_min=165000, salary_max=210000, currency="USD", priority="P2",
         business_impact="Multi-source ingestion for enterprise customers.",
         required_skills=["Python", "Airflow", "Snowflake"],
         nice_to_have=["Kafka", "Terraform"],
         hiring_manager="Kabir Nair"),
    dict(job_id="job_sales_ent_ny", title="Enterprise Account Executive",
         team_id="team_sales_us", department_id="dept_sales", level="IC5",
         location="New York, USA", country="USA",
         salary_min=140000, salary_max=180000, currency="USD", priority="P1",
         business_impact="Expand Americas book — Q1 target USD 6M new logo ARR.",
         required_skills=["Enterprise Sales", "MEDDIC", "Value Selling"],
         nice_to_have=["Account Planning"],
         hiring_manager="David Cohen"),
    dict(job_id="job_sales_gurgaon", title="Enterprise Sales Manager — India",
         team_id="team_sales_in", department_id="dept_sales", level="M4",
         location="Gurgaon, India", country="India",
         salary_min=3500000, salary_max=5500000, currency="INR", priority="P1",
         business_impact="Anchor India go-to-market team for BFSI + Retail.",
         required_skills=["Enterprise Sales", "Account Planning", "MEDDIC"],
         nice_to_have=["Value Selling"],
         hiring_manager="Ishaan Bhatt"),
    dict(job_id="job_cp_boston", title="Client Partner — Financial Services",
         team_id="team_cp", department_id="dept_success", level="M4",
         location="Boston, USA", country="USA",
         salary_min=190000, salary_max=250000, currency="USD", priority="P0",
         business_impact="Own top-3 FS relationship — USD 12M ARR.",
         required_skills=["Client Partnership", "Program Delivery", "Stakeholder Management"],
         nice_to_have=["Salesforce CPQ"],
         hiring_manager="Priya Menon"),
    dict(job_id="job_cp_mumbai", title="Client Partner — Retail",
         team_id="team_cp", department_id="dept_success", level="M4",
         location="Mumbai, India", country="India",
         salary_min=3800000, salary_max=5800000, currency="INR", priority="P2",
         business_impact="Own INR 40Cr Retail portfolio.",
         required_skills=["Client Partnership", "Stakeholder Management"],
         nice_to_have=["Program Delivery"],
         hiring_manager="Elena Rodriguez"),
]

FIRST_NAMES_IN = ["Arjun", "Priya", "Kabir", "Sneha", "Vikram", "Anaya", "Ravi",
                  "Meera", "Rohan", "Ishita", "Aditya", "Neha", "Karthik", "Divya",
                  "Nikhil", "Shreya", "Rahul", "Tara", "Aryan", "Zara"]
LAST_NAMES_IN = ["Sharma", "Iyer", "Menon", "Nair", "Kapoor", "Reddy", "Bhatt",
                 "Krishnan", "Gupta", "Kulkarni", "Rao", "Chatterjee"]
FIRST_NAMES_US = ["James", "Sarah", "Michael", "Emily", "David", "Jessica",
                  "Chris", "Lauren", "Ryan", "Ashley", "Kevin", "Rachel",
                  "Brandon", "Megan", "Ethan", "Nicole", "Tyler"]
LAST_NAMES_US = ["Patterson", "Cohen", "Rivera", "Nguyen", "Bennett", "Walker",
                 "Foster", "Reed", "Bailey", "Griffin", "Perry", "Long"]

COMPANIES_IN = ["Infosys", "TCS", "Wipro", "Accenture India", "Tech Mahindra",
                "Zoho", "Freshworks", "Flipkart", "Swiggy", "Razorpay", "Postman"]
COMPANIES_US = ["Salesforce", "Microsoft", "Databricks", "Snowflake", "AWS",
                "Deloitte", "Accenture", "Slalom", "ThoughtWorks", "IBM", "Oracle"]

STAGES_WEIGHT: list[tuple[PipelineStage, int]] = [
    (PipelineStage.SOURCED, 40),
    (PipelineStage.SCREENING, 22),
    (PipelineStage.PHONE_SCREEN, 15),
    (PipelineStage.TECHNICAL, 10),
    (PipelineStage.ONSITE, 6),
    (PipelineStage.OFFER, 4),
    (PipelineStage.HIRED, 2),
    (PipelineStage.REJECTED, 1),
]

RISK_FLAG_POOL = ["counter_offer_risk", "location_relocation", "notice_period_long",
                  "competing_offer", "role_scope_gap", "compensation_gap"]

PICTURES = [
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=srgb&fm=jpg&w=200",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?crop=entropy&cs=srgb&fm=jpg&w=200",
    "https://images.unsplash.com/photo-1699899657680-421c2c2d5064?crop=entropy&cs=srgb&fm=jpg&w=200",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?crop=entropy&cs=srgb&fm=jpg&w=200",
]


def _weighted_stage(rng: random.Random) -> PipelineStage:
    stages, weights = zip(*STAGES_WEIGHT)
    return rng.choices(stages, weights=weights, k=1)[0]


async def seed_all(db: AsyncIOMotorDatabase) -> dict[str, int]:
    world = WorldState(db)

    # ---- Organization ----
    org = Organization(
        organization_id=ORG_ID,
        name="LevelShift",
        domain="levelshift.ai",
        industry="Enterprise AI & Digital Services",
        headquarters="Bangalore + New York",
        hq_country="India",
        total_headcount=237,
        active_reqs=len(JOB_TEMPLATES),
    )
    await world.upsert_organization(org)

    # ---- Departments ----
    for dept_id, name, leader, headcount, attr, health in DEPARTMENTS:
        await world.upsert_department(Department(
            department_id=dept_id, organization_id=ORG_ID,
            name=name, leader_name=leader,
            headcount=headcount, attrition_rate=attr, health_score=health,
        ))

    # ---- Teams ----
    for team_id, dept_id, name, mgr, headcount, open_seats in TEAMS:
        await world.upsert_team(Team(
            team_id=team_id, department_id=dept_id, organization_id=ORG_ID,
            name=name, manager_name=mgr, headcount=headcount, open_seats=open_seats,
        ))

    # ---- Skills ----
    for s in SKILLS:
        await world.upsert_skill(Skill(
            skill_id=f"skill_{s.lower().replace(' ', '_').replace('&', 'and')}",
            name=s,
            category=("technical" if any(t in s for t in ("Python", "PySpark", "Kafka",
                                                          "Kubernetes", "Terraform", "PyTorch",
                                                          "Airflow", "dbt", "Snowflake",
                                                          "Databricks", "AWS", "Azure",
                                                          "LangChain", "LangGraph", "RAG",
                                                          "LLM", "Vector"))
                       else "functional" if "Salesforce" in s or "Dynamics" in s or "Power" in s
                       else "leadership" if "Client" in s or "Delivery" in s or "Stakeholder" in s
                       else "domain"),
            market_scarcity=round(random.Random(hash(s)).uniform(0.4, 0.9), 2),
        ))

    # ---- Jobs ----
    for template in JOB_TEMPLATES:
        job = Job(
            organization_id=ORG_ID,
            status=JobStatus.OPEN,
            opened_days_ago=random.Random(template["job_id"]).randint(7, 62),
            target_close_days=45,
            sensitivity=Sensitivity.INTERNAL,
            **template,
        )
        await world.upsert_job(job)

    # ---- Candidates ----
    total_candidates = 0
    for template in JOB_TEMPLATES:
        rng = random.Random(template["job_id"])
        is_india = template["country"] == "India"
        firsts, lasts = ((FIRST_NAMES_IN, LAST_NAMES_IN) if is_india
                         else (FIRST_NAMES_US, LAST_NAMES_US))
        companies = COMPANIES_IN if is_india else COMPANIES_US
        count = rng.randint(10, 18)
        for i in range(count):
            first = rng.choice(firsts); last = rng.choice(lasts)
            full = f"{first} {last}"
            years = round(rng.uniform(3.0, 14.0), 1)
            has_skills = list(template["required_skills"])
            # 65% keep all required skills; else drop one; and randomly add 1-2 nice-to-have
            if rng.random() < 0.35 and len(has_skills) > 1:
                has_skills = has_skills[:-1]
            for nth in template["nice_to_have"]:
                if rng.random() < 0.4:
                    has_skills.append(nth)
            # pepper in a few other adjacent skills
            has_skills += rng.sample([s for s in SKILLS if s not in has_skills], k=rng.randint(1, 3))
            expected = int(rng.uniform(template["salary_min"] * 0.85,
                                       template["salary_max"] * 1.15))
            stage = _weighted_stage(rng)
            risk = rng.sample(RISK_FLAG_POOL, k=rng.randint(0, 2)) if rng.random() < 0.5 else []
            # Compute a per-candidate fit score so the UI can show real numbers
            # instead of a flat 0. Skill overlap dominates; experience trims.
            req = set(template["required_skills"])
            overlap = len(req & set(has_skills)) / max(1, len(req))
            exp_fit = 1.0 - min(1.0, abs(years - 9.0) / 12.0)
            fit_score = round(0.7 * overlap + 0.3 * exp_fit + rng.uniform(-0.06, 0.06), 3)
            fit_score = max(0.2, min(0.98, fit_score))
            cand = Candidate(
                candidate_id=f"cand_{template['job_id'].replace('job_', '')}_{i:02d}",
                organization_id=ORG_ID,
                job_id=template["job_id"],
                full_name=full,
                email=f"{first.lower()}.{last.lower()}@example.{'in' if is_india else 'com'}",
                phone=None,
                location=template["location"],
                country=template["country"],
                current_title=_derive_candidate_title(template["title"], rng),
                current_company=rng.choice(companies),
                years_experience=years,
                expected_salary=expected,
                currency=template["currency"],
                skills=list(dict.fromkeys(has_skills)),
                stage=stage,
                source=rng.choice(["sourced", "referral", "applied", "agency"]),
                fit_score=fit_score,
                risk_flags=risk,
                picture=rng.choice(PICTURES),
            )
            await world.upsert_candidate(cand)
            total_candidates += 1

    # ---- Policies ----
    policies = [
        Policy(
            policy_id="pol.offer_requires_approval",
            name="Offer Extension Requires Human Approval",
            description="All offer generation and offer extension actions require human approval "
                        "regardless of AI confidence.",
            scope="cap.generate_offer",
            applies_to_roles=["*"],
            requires_human_approval=True,
        ),
        Policy(
            policy_id="pol.min_confidence_advance",
            name="Minimum Confidence to Advance Stage",
            description="Advancing a candidate stage via runtime requires >= 0.60 confidence.",
            scope="cap.advance_stage",
            min_confidence=0.60,
        ),
        Policy(
            policy_id="pol.min_confidence_screen",
            name="Minimum Confidence to Screen",
            description="Screening runs must have >= 0.50 confidence.",
            scope="cap.screen_candidate",
            min_confidence=0.50,
        ),
        Policy(
            policy_id="pol.confidential_execution",
            name="Confidential Data Handling",
            description="Any capability touching confidential data must pass through policy audit.",
            scope="*",
            max_sensitivity="confidential",
        ),
        Policy(
            policy_id="pol.recruiter_scope",
            name="Recruiter Scope of Action",
            description="Recruiters may draft outreach and screen candidates autonomously.",
            scope="cap.draft_outreach",
            applies_to_roles=["recruiter", "hiring_manager", "admin"],
        ),
    ]
    for p in policies:
        await db.policies.update_one(
            {"policy_id": p.policy_id}, {"$set": p.model_dump()}, upsert=True
        )

    # ---- Demo users ----
    demo_users = [
        {"email": "demo.recruiter@levelshift.ai", "name": "Ava Recruiter",
         "role": "recruiter"},
        {"email": "demo.manager@levelshift.ai", "name": "Marcus Manager",
         "role": "hiring_manager"},
        {"email": "demo.executive@levelshift.ai", "name": "Elena Executive",
         "role": "executive"},
    ]
    for du in demo_users:
        existing = await db.users.find_one({"email": du["email"]}, {"_id": 0})
        if not existing:
            await db.users.insert_one({
                "user_id": new_user_id(),
                "email": du["email"],
                "name": du["name"],
                "picture": PICTURES[0],
                "role": du["role"],
                "organization_id": ORG_ID,
                "created_at": utcnow_iso(),
            })

    return {
        "organizations": 1,
        "departments": len(DEPARTMENTS),
        "teams": len(TEAMS),
        "skills": len(SKILLS),
        "jobs": len(JOB_TEMPLATES),
        "candidates": total_candidates,
        "policies": len(policies),
        "demo_users": len(demo_users),
    }
