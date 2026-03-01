"""World data models for Gorafi Simulator."""

from enum import StrEnum

from pydantic import BaseModel, Field


class CountryStatus(StrEnum):
    """Country stability status (maps to LED color)."""

    STABLE = "stable"
    AGITATED = "agitated"
    CHAOS = "chaos"


class CountryState(BaseModel):
    """A country's current state."""

    code: str
    name: str
    led_x: float
    led_y: float
    stability: float = Field(default=50.0, ge=0.0, le=100.0)
    credibilite: float = Field(default=50.0, ge=0.0, le=100.0)
    active_agents: int = 0
    last_event: str = ""
    satirical_status: str = ""

    @property
    def status(self) -> CountryStatus:
        """Derive LED status from stability."""
        if self.stability >= 60:
            return CountryStatus.STABLE
        if self.stability >= 30:
            return CountryStatus.AGITATED
        return CountryStatus.CHAOS


class GlobalIndices(BaseModel):
    """The 4 global indices displayed as gauges."""

    credibilite: float = Field(default=30.0, ge=0.0, le=100.0)
    rage: float = Field(default=10.0, ge=0.0, le=100.0)
    complotisme: float = Field(default=15.0, ge=0.0, le=100.0)
    esperance_democratique: float = Field(default=85.0, ge=0.0, le=100.0)


class NewsKind(StrEnum):
    """The 3 kinds of news the Game Master proposes."""

    REAL = "real"
    FAKE = "fake"
    SATIRICAL = "satirical"


class NewsHeadline(BaseModel):
    """A global news headline proposed by the Game Master."""

    id: str = ""
    text: str  # Titre court (1 ligne)
    body: str = ""  # Article complet style Gorafi (3-4 paragraphes)
    kind: NewsKind
    stat_impact: dict[str, float] = Field(default_factory=dict)
    source_real: str | None = None  # Real source, only for kind=real
    turn: int = 0
