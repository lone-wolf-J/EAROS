"""Memory subsystem — Working, Long-term, Organizational, Recruiter, Candidate,
Hiring Manager, Conversation, Reflection memory.

Implemented as MongoDB-backed segments. Vector retrieval is stubbed (keyword
scoring) — the design is future-compatible with an embedding backend without
changing the interface.
"""
from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import utcnow_iso


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    memory_id: str
    segment: str  # working | long_term | organizational | recruiter | candidate | manager | conversation | reflection
    organization_id: Optional[str] = None
    owner_id: Optional[str] = None
    subject_id: Optional[str] = None
    content: str
    tags: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow_iso)


class Memory:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def add(self, record: MemoryRecord) -> MemoryRecord:
        await self.db.memory.insert_one(record.model_dump())
        return record

    async def query(
        self,
        segment: Optional[str] = None,
        organization_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
    ) -> list[MemoryRecord]:
        q: dict[str, Any] = {}
        if segment: q["segment"] = segment
        if organization_id: q["organization_id"] = organization_id
        if owner_id: q["owner_id"] = owner_id
        if subject_id: q["subject_id"] = subject_id
        if keyword: q["content"] = {"$regex": keyword, "$options": "i"}
        docs = await self.db.memory.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
        return [MemoryRecord(**d) for d in docs]
