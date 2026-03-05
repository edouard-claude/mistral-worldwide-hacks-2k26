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


class AgentRanking(BaseModel):
    """A single ranking entry from phase 4 voting."""

    agent_id: str
    score: int


class AgentReaction(BaseModel):
    """An agent's reaction to a player action — includes all 4 debate phases."""

    agent_id: str
    turn: int
    action_id: str
    reaction_text: str = ""
    stat_changes: dict[str, float] = Field(default_factory=dict)
    level_change: AgentLevel | None = None
    headline: str = ""
    # Rich per-phase data from swarm arena
    phase1_reasoning: str = ""
    phase2_take: str = ""
    phase3_revision: str = ""
    phase4_vote: str = ""
    confidence_initial: int = 0
    confidence_final: int = 0
    rankings: list[AgentRanking] = Field(default_factory=list)
    new_color: float | None = None
    is_error: bool = False
