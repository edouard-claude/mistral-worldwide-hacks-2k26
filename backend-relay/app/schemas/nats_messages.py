from typing import Any

from pydantic import BaseModel


# --- Models used in code ---


class ArenaEvent(BaseModel):
    """Envelope sent to WebSocket clients: subject + raw payload from NATS."""

    subject: str
    data: Any


class FakeNewsInput(BaseModel):
    """HTTP input from the game master."""

    content: str


# --- Documentation / reference models (match Go game contracts) ---


class InputWaiting(BaseModel):
    round: int
    waiting: bool


class RoundStart(BaseModel):
    round: int
    fake_news: str
    context: Any


class PhaseStart(BaseModel):
    round: int
    phase: int


class AgentInput(BaseModel):
    phase: int
    data: Any


class AgentOutput(BaseModel):
    data: dict[str, Any] = {}


class AgentStatus(BaseModel):
    state: str
    detail: str


class AgentKill(BaseModel):
    reason: str
    round: int


class EventDeath(BaseModel):
    agent_id: str
    agent_name: str
    round: int
    cause: str


class EventClone(BaseModel):
    parent_id: str
    child_id: str
    child_name: str
    round: int


class EventEnd(BaseModel):
    survivors: list[Any]
    history: list[Any]
