"""Modeles Pydantic pour la gamification."""

from pydantic import BaseModel
from typing import Optional, List


class PlayerState(BaseModel):
    xp: int = 0
    level: int = 1
    title: str = "Nouveau Venu"
    streak_days: int = 0
    streak_best: int = 0
    last_active_date: str = ""
    joined_at: str = ""
    total_messages: int = 0
    total_calls: int = 0
    total_visio: int = 0
    total_instructions: int = 0
    total_contacts: int = 0
    total_notes: int = 0
    profile_fields: int = 0
    badges_count: int = 0
    missions_completed: int = 0
    tabs_visited: str = ""
    days_active: int = 0
    stars: int = 0

    def to_redis(self) -> dict:
        return {k: str(v) for k, v in self.model_dump().items()}

    @classmethod
    def from_redis(cls, data: dict) -> "PlayerState":
        if not data:
            return cls()
        int_fields = {
            "xp", "level", "streak_days", "streak_best",
            "total_messages", "total_calls", "total_visio",
            "total_instructions", "total_contacts", "total_notes",
            "profile_fields", "badges_count", "missions_completed",
            "days_active", "stars",
        }
        parsed = {}
        for k, v in data.items():
            if k in int_fields:
                try:
                    parsed[k] = int(v)
                except (ValueError, TypeError):
                    parsed[k] = 0
            else:
                parsed[k] = v or ""
        return cls(**parsed)


class Badge(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    rarity: str
    earned: bool = False
    earned_at: Optional[str] = None


class Mission(BaseModel):
    id: str
    type: str
    title: str
    description: str
    category: str
    progress: int = 0
    target: int = 1
    progress_percent: float = 0.0
    xp_reward: int = 0
    status: str = "active"
    started_at: str = ""
    completed_at: str = ""
    action_type: str = ""
    counter_field: str = ""
    collected: bool = False

    def to_redis(self) -> dict:
        return {k: str(v) for k, v in self.model_dump().items()}

    @classmethod
    def from_redis(cls, mission_id: str, data: dict) -> "Mission":
        if not data:
            return cls(id=mission_id, type="unknown", title="?", description="?", category="?")
        int_fields = {"progress", "target", "xp_reward"}
        parsed = {"id": mission_id}
        for k, v in data.items():
            if k == "id":
                continue
            if k in int_fields:
                try:
                    parsed[k] = int(v)
                except (ValueError, TypeError):
                    parsed[k] = 0
            elif k == "collected":
                parsed[k] = v in ("True", "true", "1")
            elif k == "progress_percent":
                try:
                    parsed[k] = float(v)
                except (ValueError, TypeError):
                    parsed[k] = 0.0
            else:
                parsed[k] = v or ""
        return cls(**parsed)


class ActivityEvent(BaseModel):
    id: str
    type: str
    message: str
    icon: str
    timestamp: str
    metadata: dict = {}


class StabilityGauge(BaseModel):
    score: int = 70
    trend: str = "stable"
    regularity: int = 70
    engagement: int = 70
    mood: int = 70
    updated_at: str = ""

    def to_redis(self) -> dict:
        return {k: str(v) for k, v in self.model_dump().items()}

    @classmethod
    def from_redis(cls, data: dict) -> "StabilityGauge":
        if not data:
            return cls()
        int_fields = {"score", "regularity", "engagement", "mood"}
        parsed = {}
        for k, v in data.items():
            if k in int_fields:
                try:
                    parsed[k] = int(v)
                except (ValueError, TypeError):
                    parsed[k] = 70
            else:
                parsed[k] = v or ""
        return cls(**parsed)


class CollectRewardRequest(BaseModel):
    mission_id: str
