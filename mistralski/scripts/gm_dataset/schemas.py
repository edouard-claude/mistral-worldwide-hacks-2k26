"""Pydantic models for Game Master output validation.

Defines the 4 GM output types: temperature, headlines, reaction, narrative.
Each has a strict JSON schema for fine-tuning dataset validation.
"""

from pydantic import BaseModel, Field, field_validator

from scripts.gm_dataset.constants import (
    ACTION_IDS,
    COUNTRY_CODES,
    HEADLINE_STYLES,
    INDEX_NAMES,
)


class HeadlineOutput(BaseModel):
    """A single satirical headline in GM output."""

    id: str = Field(description="Unique ID like t4_h01")
    text: str = Field(max_length=200, description="Satirical headline, max 200 chars")
    style: str = Field(description="gorafi | onion | raw")
    type: str = Field(description="One of 20 action IDs")
    target_countries: list[str] = Field(
        min_length=1, max_length=5,
        description="ISO 2-letter country codes",
    )
    stat_impact: dict[str, float] = Field(description="Impact on global indices")
    virality: int = Field(ge=1, le=10, description="Virality score 1-10")
    source_real: str | None = Field(
        default=None,
        description="Real headline that inspired this, or null",
    )

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        if v not in HEADLINE_STYLES:
            raise ValueError(f"style must be one of {HEADLINE_STYLES}, got '{v}'")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ACTION_IDS:
            raise ValueError(f"type must be a valid action ID, got '{v}'")
        return v

    @field_validator("target_countries")
    @classmethod
    def validate_countries(cls, v: list[str]) -> list[str]:
        valid = set(COUNTRY_CODES + ["MONDIAL"])
        for code in v:
            if code not in valid:
                raise ValueError(f"Invalid country code: '{code}'")
        return v

    @field_validator("stat_impact")
    @classmethod
    def validate_stat_impact(cls, v: dict[str, float]) -> dict[str, float]:
        for key in v:
            if key not in INDEX_NAMES:
                raise ValueError(f"Invalid index in stat_impact: '{key}'")
        return v


# --- GM Temperature Output (1x at game start) ---

class GMTemperatureOutput(BaseModel):
    """Output for gm_temperature: sets the mood at game start."""

    type: str = Field(default="gm_temperature")
    headline: HeadlineOutput
    narrative: str = Field(
        min_length=20, max_length=500,
        description="Satirical narrative setting the day's tone",
    )
    mood: str = Field(
        min_length=3, max_length=50,
        description="One-word or short mood descriptor",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "gm_temperature":
            raise ValueError("type must be 'gm_temperature'")
        return v


# --- GM Headlines Output (start of each turn) ---

class GMHeadlinesOutput(BaseModel):
    """Output for gm_headlines: 3-5 headlines + ticker text per turn."""

    type: str = Field(default="gm_headlines")
    headlines: list[HeadlineOutput] = Field(
        min_length=3, max_length=5,
        description="3-5 satirical headlines for this turn",
    )
    ticker_text: str = Field(
        min_length=20, max_length=300,
        description="CNN-style scrolling ticker text",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "gm_headlines":
            raise ValueError("type must be 'gm_headlines'")
        return v


# --- GM Reaction Output (after each player action) ---

class GMReactionOutput(BaseModel):
    """Output for gm_reaction: reaction to a player action."""

    type: str = Field(default="gm_reaction")
    headlines: list[HeadlineOutput] = Field(
        min_length=1, max_length=3,
        description="1-3 reaction headlines",
    )
    narrative_impact: str = Field(
        min_length=20, max_length=400,
        description="Satirical description of the action's impact",
    )
    agent_reactions_hint: list[str] = Field(
        min_length=1, max_length=5,
        description="Short hints about how agents might react",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "gm_reaction":
            raise ValueError("type must be 'gm_reaction'")
        return v


# --- GM Narrative Output (every 2-3 turns) ---

class GMNarrativeOutput(BaseModel):
    """Output for gm_narrative: world assessment narrative."""

    type: str = Field(default="gm_narrative")
    headlines: list[HeadlineOutput] = Field(
        min_length=1, max_length=2,
        description="1-2 narrative headlines",
    )
    narrative_lines: list[str] = Field(
        min_length=3, max_length=5,
        description="3-5 lines of satirical world narrative",
    )
    world_assessment: str = Field(
        min_length=20, max_length=300,
        description="Overall world state assessment",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "gm_narrative":
            raise ValueError("type must be 'gm_narrative'")
        return v


# --- Type mapping ---

GM_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "gm_temperature": GMTemperatureOutput,
    "gm_headlines": GMHeadlinesOutput,
    "gm_reaction": GMReactionOutput,
    "gm_narrative": GMNarrativeOutput,
}
