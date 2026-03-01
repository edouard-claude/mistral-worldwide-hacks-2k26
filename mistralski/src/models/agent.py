"""Agent data models for Gorafi Simulator."""

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentLevel(StrEnum):
    """Agent influence level."""

    PASSIF = "passif"
    ACTIF = "actif"
    LEADER = "leader"


class AgentStats(BaseModel):
    """Agent stat bars."""

    croyance: float = Field(default=50.0, ge=0.0, le=100.0)
    confiance: float = Field(default=50.0, ge=0.0, le=100.0)
    richesse: float = Field(default=50.0, ge=0.0, le=100.0)


class AgentState(BaseModel):
    """Full agent state at a given turn."""

    agent_id: str
    name: str
    personality: str
    country: str
    avatar: str = "default"
    stats: AgentStats = Field(default_factory=AgentStats)
    level: AgentLevel = AgentLevel.PASSIF
    status_text: str = ""
    is_neutralized: bool = False
    turn: int = 0


class AgentReaction(BaseModel):
    """An agent's reaction to a player action."""

    agent_id: str
    turn: int
    action_id: str
    reaction_text: str = ""
    stat_changes: dict[str, float] = Field(default_factory=dict)
    level_change: AgentLevel | None = None
    headline: str = ""
