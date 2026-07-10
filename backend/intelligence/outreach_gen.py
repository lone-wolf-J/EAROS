"""Outreach Intelligence — multi-channel personalized outreach with A/B."""
from __future__ import annotations

import random
from typing import Any

from platform_core.world import WorldState


TONES = {
    "warm": {"opener": "Hope you're having a great week", "close": "Warm regards"},
    "direct": {"opener": "Quick note", "close": "Best"},
    "curiosity": {"opener": "This one might interest you", "close": "Curiously"},
}


async def draft_outreach_pack(world: WorldState, organization_id: str,
                              candidate_id: str) -> dict[str, Any]:
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return {"error": "candidate not found"}
    job = await world.get_job(cand.job_id)
    if not job:
        return {"error": "job not found"}

    r = random.Random(f"{candidate_id}-outreach")
    first = cand.full_name.split()[0]
    top_skills = ", ".join(cand.skills[:3])

    def _email(tone_key: str) -> dict[str, Any]:
        tone = TONES[tone_key]
        subject = (
            f"{job.title} @ LevelShift — a role we think matches your profile"
            if tone_key == "warm" else
            f"Quick opportunity: {job.title} at LevelShift"
            if tone_key == "direct" else
            f"{first}, a {job.title} role — worth 10 minutes?"
        )
        body = (
            f"{tone['opener']}, {first}.\n\n"
            f"I'm reaching out from LevelShift about a {job.title} role in {job.location}. "
            f"Your background at {cand.current_company} — particularly your {top_skills} — "
            f"aligns with what {job.hiring_manager}'s team is scaling towards. "
            f"The team owns {job.business_impact.lower()}\n\n"
            f"Would you be open to a 20-minute intro this week? "
            f"I can share the JD and comp band up front.\n\n"
            f"{tone['close']},\nLevelShift Talent"
        )
        return {"subject": subject, "body": body, "tone": tone_key,
                "channel": "email",
                "response_probability": round(
                    0.14 + (0.02 if tone_key == "warm" else 0)
                    + (0.03 if "referral" in cand.source else 0), 3)}

    linkedin = {
        "channel": "linkedin_inmail",
        "subject": f"{first} — {job.title} opening at LevelShift",
        "body": (
            f"{first} — noticed your {top_skills} work at {cand.current_company}. "
            f"We're hiring a {job.title} for {job.location}. "
            "Open to a short chat? I'll respect your time — 15 minutes is enough."
        ),
        "response_probability": 0.11,
        "tone": "professional",
    }
    sms = {
        "channel": "sms",
        "body": (
            f"Hi {first}, this is LevelShift Talent. Interested in a "
            f"{job.title} role in {job.location.split(',')[0]}? "
            "Reply YES for details."
        ),
        "response_probability": 0.08,
        "tone": "concise",
    }
    whatsapp = {
        "channel": "whatsapp",
        "body": (
            f"Hi {first} 👋 — {job.title} at LevelShift in {job.location.split(',')[0]}. "
            "Quick chat this week? Happy to share JD + band."
        ),
        "response_probability": 0.19,
        "tone": "casual",
    }
    voice_script = {
        "channel": "voice",
        "body": (
            f"Hi {first}, this is LevelShift Talent. I'm calling about a "
            f"{job.title} opportunity based in {job.location.split(',')[0]}. "
            "I'd love five minutes to walk you through the team and the comp "
            "band before you decide if it's worth a deeper conversation."
        ),
        "response_probability": 0.22,
        "tone": "professional",
    }

    followup_sequence = [
        {"day": 3, "channel": "email",
         "hint": "Reference original message; offer a specific 15-min window."},
        {"day": 7, "channel": "linkedin_inmail",
         "hint": "Share a concrete team artifact — engineering blog / talk."},
        {"day": 12, "channel": "sms",
         "hint": "Short, respectful close — ‘if timing isn't right, no worries.’"},
    ]

    return {
        "candidate_id": candidate_id,
        "candidate_name": cand.full_name,
        "job_id": job.job_id,
        "job_title": job.title,
        "channels": {
            "email_variants": [_email("warm"), _email("direct"), _email("curiosity")],
            "linkedin": linkedin,
            "sms": sms,
            "whatsapp": whatsapp,
            "voice_script": voice_script,
        },
        "recommended_send_order": ["email:warm", "linkedin", "whatsapp",
                                    "email:direct"],
        "expected_response_probability": 0.31,
        "follow_up_sequence": followup_sequence,
        "personalization_signals": [
            f"Current company: {cand.current_company}",
            f"Top skills: {top_skills}",
            f"Location: {cand.location}",
        ],
        "reasoning": [
            "Warm tone chosen as the primary — highest response rate for cold "
            "senior candidates in our historical sample.",
            "LinkedIn used as a follow-up (not lead) due to InMail rate limits.",
            "SMS reserved for confirmation flow post-response.",
        ],
    }
