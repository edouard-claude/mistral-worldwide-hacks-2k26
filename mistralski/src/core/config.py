"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Game of Claw configuration."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # vLLM GPU Server (Scaleway)
    vllm_base_url: str = "http://gpu-server:8000"
    vllm_api_key: SecretStr = SecretStr("")
    vllm_agent_model: str = "mistralai/Mistral-Small-3.2-24B-Instruct-2503"
    vllm_mutation_model: str = "mistralai/Devstral-Small-2507"

    # OSRM Routing
    osrm_base_url: str = "http://localhost:5000"

    # Qdrant Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "agent_memories"
    qdrant_vector_size: int = 1024

    # DuckDB
    duckdb_path: str = "data/game.duckdb"

    # Game Master LLM (Mistral Large API)
    mistral_api_key: SecretStr = SecretStr("")
    mistral_gm_model: str = "mistral-large-latest"

    # OpenWeatherMap
    openweathermap_api_key: str = ""

    # Game parameters
    tick_rate_ms: int = 100
    time_compression: int = 600
    perception_radius_m: float = 500.0
    initial_agent_count: int = 10
    target_city: str = "paris"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
