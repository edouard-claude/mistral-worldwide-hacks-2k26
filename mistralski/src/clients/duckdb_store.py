"""DuckDB game state persistence with spatial extension."""

import asyncio
from pathlib import Path
from typing import Any

import duckdb
import structlog

from src.core.config import Settings
from src.core.exceptions import StorageError
from src.models.agent import AgentState
from src.models.world import POI, POICategory

logger = structlog.get_logger(__name__)


class GameStore:
    """DuckDB-backed game state store with spatial queries."""

    def __init__(self, settings: Settings) -> None:
        self._db_path = settings.duckdb_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection."""
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self._db_path)
            self._conn.execute("INSTALL spatial; LOAD spatial;")
        return self._conn

    def init_schema(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                personality VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                agent_id VARCHAR NOT NULL,
                tick INTEGER NOT NULL,
                lat DOUBLE NOT NULL,
                lon DOUBLE NOT NULL,
                energy DOUBLE,
                health DOUBLE,
                hunger DOUBLE,
                money DOUBLE,
                reputation DOUBLE,
                stress DOUBLE,
                knowledge DOUBLE,
                life_number INTEGER DEFAULT 1,
                death_count INTEGER DEFAULT 0,
                current_action VARCHAR,
                prompt_version INTEGER DEFAULT 1,
                geom GEOMETRY,
                PRIMARY KEY (agent_id, tick)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                description VARCHAR,
                severity VARCHAR,
                lat DOUBLE NOT NULL,
                lon DOUBLE NOT NULL,
                radius_m DOUBLE DEFAULT 200,
                start_tick INTEGER NOT NULL,
                end_tick INTEGER,
                effects VARCHAR,
                geom GEOMETRY
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                description VARCHAR,
                reward VARCHAR,
                lat DOUBLE NOT NULL,
                lon DOUBLE NOT NULL,
                radius_m DOUBLE DEFAULT 100,
                start_tick INTEGER NOT NULL,
                deadline_tick INTEGER NOT NULL,
                status VARCHAR DEFAULT 'active',
                assigned_agent_id VARCHAR
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pois (
                poi_id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                lat DOUBLE NOT NULL,
                lon DOUBLE NOT NULL,
                osm_tags VARCHAR,
                geom GEOMETRY
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                agent_id VARCHAR NOT NULL,
                version INTEGER NOT NULL,
                prompt_text VARCHAR NOT NULL,
                created_at_tick INTEGER NOT NULL,
                mutation_reason VARCHAR,
                PRIMARY KEY (agent_id, version)
            )
        """)
        logger.info("duckdb_schema_initialized")

    async def save_agent_state(self, state: AgentState) -> None:
        """Persist agent state for a tick.

        Args:
            state: The agent state to save.
        """

        def _save() -> None:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_states
                (agent_id, tick, lat, lon, energy, health, hunger, money,
                 reputation, stress, knowledge, life_number, death_count,
                 current_action, prompt_version, geom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ST_Point(?, ?))
                """,
                [
                    state.agent_id,
                    state.tick,
                    state.lat,
                    state.lon,
                    state.vitals.energy,
                    state.vitals.health,
                    state.vitals.hunger,
                    state.vitals.money,
                    state.vitals.reputation,
                    state.vitals.stress,
                    state.vitals.knowledge,
                    state.life_number,
                    state.death_count,
                    state.current_action.value if state.current_action else None,
                    state.current_prompt_version,
                    state.lon,
                    state.lat,
                ],
            )

        await asyncio.to_thread(_save)

    async def get_nearby_pois(self, lat: float, lon: float, radius_m: float) -> list[POI]:
        """Find POIs within radius of a point.

        Args:
            lat: Latitude of center point.
            lon: Longitude of center point.
            radius_m: Search radius in meters.

        Returns:
            List of nearby POIs.
        """

        def _query() -> list[dict[str, Any]]:
            conn = self._get_conn()
            # Approximate degree conversion: 1 degree ~ 111320m at equator
            degree_radius = radius_m / 111320.0
            result = conn.execute(
                """
                SELECT poi_id, name, category, lat, lon, osm_tags
                FROM pois
                WHERE ST_DWithin(geom, ST_Point(?, ?), ?)
                """,
                [lon, lat, degree_radius],
            ).fetchall()
            columns = ["poi_id", "name", "category", "lat", "lon", "osm_tags"]
            return [dict(zip(columns, row, strict=False)) for row in result]

        try:
            rows = await asyncio.to_thread(_query)
            return [
                POI(
                    poi_id=r["poi_id"],
                    name=r["name"],
                    category=POICategory(r["category"]),
                    lat=r["lat"],
                    lon=r["lon"],
                )
                for r in rows
            ]
        except Exception as e:
            raise StorageError(f"DuckDB POI query failed: {e}") from e

    async def get_nearby_agents(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        current_tick: int,
        exclude_id: str = "",
    ) -> list[AgentState]:
        """Find agents within radius at a given tick.

        Args:
            lat: Center latitude.
            lon: Center longitude.
            radius_m: Search radius in meters.
            current_tick: The tick to query.
            exclude_id: Agent ID to exclude (self).

        Returns:
            List of nearby agent states.
        """

        def _query() -> list[dict[str, Any]]:
            conn = self._get_conn()
            degree_radius = radius_m / 111320.0
            result = conn.execute(
                """
                SELECT agent_id, lat, lon, energy, health, hunger,
                       money, reputation, stress, knowledge,
                       life_number, death_count, current_action
                FROM agent_states
                WHERE tick = ?
                  AND agent_id != ?
                  AND ST_DWithin(geom, ST_Point(?, ?), ?)
                """,
                [current_tick, exclude_id, lon, lat, degree_radius],
            ).fetchall()
            columns = [
                "agent_id",
                "lat",
                "lon",
                "energy",
                "health",
                "hunger",
                "money",
                "reputation",
                "stress",
                "knowledge",
                "life_number",
                "death_count",
                "current_action",
            ]
            return [dict(zip(columns, row, strict=False)) for row in result]

        try:
            rows = await asyncio.to_thread(_query)
            from src.models.agent import ActionType, AgentVitals

            agents: list[AgentState] = []
            for r in rows:
                agents.append(
                    AgentState(
                        agent_id=r["agent_id"],
                        name="",
                        personality="",
                        lat=r["lat"],
                        lon=r["lon"],
                        vitals=AgentVitals(
                            energy=r["energy"],
                            health=r["health"],
                            hunger=r["hunger"],
                            money=r["money"],
                            reputation=r["reputation"],
                            stress=r["stress"],
                            knowledge=r["knowledge"],
                        ),
                        life_number=r["life_number"],
                        death_count=r["death_count"],
                        current_action=(
                            ActionType(r["current_action"]) if r["current_action"] else None
                        ),
                        tick=current_tick,
                    )
                )
            return agents
        except Exception as e:
            raise StorageError(f"DuckDB agent query failed: {e}") from e

    async def health_check(self) -> bool:
        """Check if DuckDB is operational with spatial extension."""

        def _check() -> bool:
            conn = self._get_conn()
            result = conn.execute("SELECT ST_Point(2.35, 48.85)").fetchone()
            return result is not None

        try:
            return await asyncio.to_thread(_check)
        except Exception:
            return False

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
