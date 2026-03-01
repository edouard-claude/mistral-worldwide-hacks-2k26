"""Verify all service connections are working.

Usage: python scripts/test_connections.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.logging import setup_logging


async def main() -> None:
    setup_logging()
    settings = get_settings()

    results: list[tuple[str, bool, str]] = []

    # 1. vLLM
    try:
        from src.clients.vllm import VLLMBatchClient

        client = VLLMBatchClient(settings)
        ok = await client.health_check()
        await client.close()
        results.append(("vLLM", ok, settings.vllm_base_url))
    except Exception as e:
        results.append(("vLLM", False, str(e)))

    # 2. OSRM
    try:
        from src.clients.osrm import OSRMClient

        client = OSRMClient(settings)
        ok = await client.health_check()
        await client.close()
        results.append(("OSRM", ok, settings.osrm_base_url))
    except Exception as e:
        results.append(("OSRM", False, str(e)))

    # 3. Qdrant
    try:
        from src.clients.qdrant import QdrantMemoryClient

        client = QdrantMemoryClient(settings)
        ok = await client.health_check()
        await client.close()
        results.append(("Qdrant", ok, settings.qdrant_url))
    except Exception as e:
        results.append(("Qdrant", False, str(e)))

    # 4. DuckDB + Spatial
    try:
        from src.clients.duckdb_store import GameStore

        store = GameStore(settings)
        ok = await store.health_check()
        store.close()
        results.append(("DuckDB+Spatial", ok, settings.duckdb_path))
    except Exception as e:
        results.append(("DuckDB+Spatial", False, str(e)))

    # 5. OpenWeatherMap
    try:
        from src.clients.weather import WeatherClient

        client = WeatherClient(settings)
        ok = await client.health_check()
        await client.close()
        results.append(("OpenWeatherMap", ok, "api.openweathermap.org"))
    except Exception as e:
        results.append(("OpenWeatherMap", False, str(e)))

    # 6. RSS Feeds
    try:
        from src.clients.news import NewsClient

        client = NewsClient()
        ok = await client.health_check()
        results.append(("RSS Feeds", ok, "feedparser"))
    except Exception as e:
        results.append(("RSS Feeds", False, str(e)))

    # Print results
    print("\n" + "=" * 55)
    print("  Game of Claw — Connection Status")
    print("=" * 55)
    all_ok = True
    for name, ok, detail in results:
        status = "\033[92mOK\033[0m" if ok else "\033[91mFAIL\033[0m"
        if not ok:
            all_ok = False
        print(f"  {name:<18} [{status}]  {detail}")
    print("=" * 55)

    if not all_ok:
        print("\n  Some services are unavailable. Check docker-compose and .env")
        sys.exit(1)
    else:
        print("\n  All services operational!")


if __name__ == "__main__":
    asyncio.run(main())
