"""Resume Intelligence.

Extracts structure, computes fit against a job, produces client + internal
versions, and highlights strengths / gaps / red flags.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from platform_core.world import WorldState


SKILL_LEXICON = [
    "java", "spring boot", "spring", "kafka", "microservices", "kubernetes",
    "docker", "aws", "azure", "gcp", "terraform", "ansible", "python",
    "pytorch", "tensorflow", "langchain", "langgraph", "rag", "llm ops",
    "vector databases", "salesforce apex", "salesforce lwc", "salesforce cpq",
    "dynamics 365 ce", "dynamics 365 f&o", "power platform", "power automate",
    "databricks", "snowflake", "pyspark", "dbt", "airflow", "sql",
    "enterprise sales", "meddic", "value selling", "account planning",
    "client partnership", "stakeholder management", "program delivery",
    "banking", "fintech", "retail", "healthcare", "insurance",
]


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for s in SKILL_LEXICON:
        if s in lower and s not in found:
            found.append(s)
    return found


def _extract_years(text: str) -> Optional[float]:
    m = re.search(r"(\d{1,2})\s*\+?\s*(?:years|yrs|yr)", text.lower())
    if m:
        return float(m.group(1))
    return None


def _extract_email(text: str) -> Optional[str]:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return m.group(0) if m else None


def _extract_phone(text: str) -> Optional[str]:
    m = re.search(r"(\+?\d[\d\-\s]{7,}\d)", text)
    return m.group(0) if m else None


def _extract_title_and_company(text: str) -> tuple[str, str]:
    # very loose: first uppercase line with "@" or " at "
    for line in text.splitlines()[:8]:
        m = re.match(r"([A-Z][^@\n]{5,60})\s+(?:@|at)\s+([A-Za-z][A-Za-z0-9\s\.\-&]+)", line.strip())
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return "", ""


def parse_resume(raw_text: str) -> dict[str, Any]:
    """Deterministic parser — no LLM required for demo path."""
    skills = _extract_skills(raw_text)
    years = _extract_years(raw_text) or 0.0
    email = _extract_email(raw_text)
    phone = _extract_phone(raw_text)
    title, company = _extract_title_and_company(raw_text)
    # crude section detection
    sections = {}
    for header in ["experience", "education", "projects", "skills",
                   "certifications", "summary"]:
        m = re.search(rf"\n\s*{header}\s*\n", raw_text, re.IGNORECASE)
        if m:
            sections[header] = True
    return {
        "email": email,
        "phone": phone,
        "current_title": title,
        "current_company": company,
        "years_experience_detected": years,
        "skills_detected": skills,
        "sections_detected": sorted(sections.keys()),
        "word_count": len(raw_text.split()),
    }


async def fit_analysis(world: WorldState, job_id: str,
                       parsed: dict[str, Any]) -> dict[str, Any]:
    job = await world.get_job(job_id)
    if not job:
        return {"error": "job not found"}

    req = set(s.lower() for s in job.required_skills)
    have = set(s.lower() for s in parsed.get("skills_detected", []))
    matched = sorted(req & have)
    missing = sorted(req - have)
    coverage = len(matched) / max(1, len(req))
    years = float(parsed.get("years_experience_detected") or 0)
    exp_fit = min(1.0, years / 8.0)
    fit_score = round(0.65 * coverage + 0.35 * exp_fit, 3)

    strengths = []
    if coverage >= 0.7:
        strengths.append(f"Skill coverage {coverage:.0%} of required stack")
    if years >= 8:
        strengths.append(f"Seniority signal ({years:.0f} yrs)")
    if "banking" in have or "fintech" in have:
        strengths.append("Domain-adjacent (financial services)")
    if not strengths:
        strengths.append("Signals present but shallow — deeper screen recommended")

    weaknesses = []
    if coverage < 0.5:
        weaknesses.append(f"Only {coverage:.0%} of required skills detected")
    if years and years < 6:
        weaknesses.append("Sub-band experience")
    if not parsed.get("sections_detected"):
        weaknesses.append("Resume structure is thin — no clear sections")
    if not parsed.get("email"):
        weaknesses.append("No contact email detected")

    return {
        "job_id": job.job_id,
        "job_title": job.title,
        "coverage": round(coverage, 3),
        "experience_fit": round(exp_fit, 3),
        "fit_score": fit_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def redact(parsed: dict[str, Any]) -> dict[str, Any]:
    """Client-safe redaction."""
    return {
        **parsed,
        "email": "[redacted]" if parsed.get("email") else None,
        "phone": "[redacted]" if parsed.get("phone") else None,
    }


def client_summary(parsed: dict[str, Any], fit: dict[str, Any],
                   candidate_alias: str = "Candidate-A") -> dict[str, Any]:
    """One-page client submission summary (redacted)."""
    return {
        "candidate_alias": candidate_alias,
        "current_title": parsed.get("current_title") or "Senior Engineer",
        "current_company": "[redacted]",
        "years_experience": parsed.get("years_experience_detected") or 0,
        "match_summary": (
            f"Fit {fit['fit_score']:.2f} against {fit['job_title']} · "
            f"skill coverage {fit['coverage']:.0%}"
        ),
        "highlighted_skills": fit.get("matched_skills", [])[:8],
        "growth_areas": fit.get("missing_skills", [])[:5],
        "prepared_for": "Client hiring manager",
    }
