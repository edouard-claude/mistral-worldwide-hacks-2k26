"""Top-level game state models for Gorafi Simulator."""

from pydantic import BaseModel, Field

from src.models.agent import AgentReaction, AgentState
from src.models.world import GlobalIndices, NewsHeadline


class GameState(BaseModel):
    """Complete game state."""

    turn: int = 1
    max_turns: int = 10
    indices: GlobalIndices = Field(default_factory=GlobalIndices)
    agents: list[AgentState] = Field(default_factory=list)
    headlines_history: list[NewsHeadline] = Field(default_factory=list)
    indice_mondial_decerebration: float = 0.0  # 0-100


class NewsProposal(BaseModel):
    """3 global news proposed by the GM for the player to choose from."""

    turn: int
    real: NewsHeadline
    fake: NewsHeadline
    satirical: NewsHeadline
    gm_commentary: str = ""


class NewsChoice(BaseModel):
    """The player's chosen news + its game impact."""

    turn: int
    chosen: NewsHeadline
    index_deltas: dict[str, float] = Field(default_factory=dict)
    chaos_bonus: float = 0.0
    virality: float = 0.0
    gm_reaction: str = ""


class TurnReport(BaseModel):
    """End-of-turn report sent to the GM."""

    turn: int
    chosen_news: NewsHeadline
    indices_before: GlobalIndices
    indices_after: GlobalIndices
    agent_reactions: list[AgentReaction] = Field(default_factory=list)
    agents_neutralized: list[str] = Field(default_factory=list)
    agents_promoted: list[str] = Field(default_factory=list)
    decerebration: float = 0.0


class GMStrategy(BaseModel):
    """GM's long-term strategy to maximize chaos."""

    turn: int
    analysis: str = ""  # What happened, what worked, what didn't
    threat_agents: list[str] = Field(default_factory=list)  # Agents resisting most
    weak_spots: list[str] = Field(default_factory=list)  # Exploitable weaknesses
    next_turn_plan: str = ""  # What kind of news to push next
    long_term_goal: str = ""  # Multi-turn strategy
    # Internal — player manipulation (NEVER sent to frontend)
    desired_pick: str = ""  # "real", "fake", or "satirical" — what we want the player to choose
    manipulation_tactic: str = ""  # How to steer the player toward desired_pick
