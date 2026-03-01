"""Tests for DuckDB game store with spatial extension."""

import contextlib
import os
import tempfile

import pytest

from src.clients.duckdb_store import GameStore
from src.core.config import Settings
from src.models.agent import AgentState, AgentVitals


@pytest.fixture
def tmp_db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    os.unlink(path)  # DuckDB creates the file itself
    yield path
    # Cleanup
    for ext in ["", ".wal"]:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path + ext)


@pytest.fixture
def settings(tmp_db_path: str) -> Settings:
    return Settings(duckdb_path=tmp_db_path)


@pytest.fixture
def store(settings: Settings) -> GameStore:
    s = GameStore(settings)
    s.init_schema()
    return s


def test_init_schema(store: GameStore) -> None:
    """Schema creation should succeed without errors."""
    # init_schema already called in fixture
    assert store.health_check


@pytest.mark.asyncio
async def test_health_check(store: GameStore) -> None:
    result = await store.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_save_and_query_agent_state(store: GameStore) -> None:
    state = AgentState(
        agent_id="agent_01",
        name="Lucien",
        personality="Pragmatic",
        lat=48.8566,
        lon=2.3522,
        vitals=AgentVitals(energy=75.0, health=90.0, hunger=30.0, money=100.0),
        tick=1,
    )
    await store.save_agent_state(state)

    # Query nearby agents
    agents = await store.get_nearby_agents(
        lat=48.8566,
        lon=2.3522,
        radius_m=1000.0,
        current_tick=1,
        exclude_id="other_agent",
    )
    assert len(agents) == 1
    assert agents[0].agent_id == "agent_01"


@pytest.mark.asyncio
async def test_get_nearby_agents_excludes_self(store: GameStore) -> None:
    state = AgentState(
        agent_id="agent_01",
        name="Test",
        personality="Test",
        lat=48.8566,
        lon=2.3522,
        tick=1,
    )
    await store.save_agent_state(state)

    agents = await store.get_nearby_agents(
        lat=48.8566,
        lon=2.3522,
        radius_m=1000.0,
        current_tick=1,
        exclude_id="agent_01",
    )
    assert len(agents) == 0


@pytest.mark.asyncio
async def test_get_nearby_pois_empty(store: GameStore) -> None:
    pois = await store.get_nearby_pois(lat=48.8566, lon=2.3522, radius_m=500.0)
    assert pois == []


def test_close(store: GameStore) -> None:
    store.close()
    # Should not raise on double close
    store.close()
