"""OpenWeatherMap client with cache."""

import time

import httpx
import structlog
from pydantic import BaseModel

from src.core.config import Settings

logger = structlog.get_logger(__name__)

_CACHE_TTL_S = 1800  # 30 minutes


class WeatherData(BaseModel):
    """Current weather conditions."""

    temperature_c: float
    feels_like_c: float
    humidity: int
    wind_speed_ms: float
    visibility_m: int
    description: str
    rain_mm: float = 0.0
    snow_mm: float = 0.0


class WeatherClient:
    """OpenWeatherMap API client with 30-minute cache."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openweathermap_api_key
        self._client = httpx.AsyncClient(
            base_url="https://api.openweathermap.org",
            timeout=10.0,
        )
        self._cache: WeatherData | None = None
        self._cache_time: float = 0.0

    async def get_current(self, city: str = "Paris") -> WeatherData:
        """Get current weather for a city.

        Args:
            city: City name.

        Returns:
            Current weather data.
        """
        now = time.monotonic()
        if self._cache and (now - self._cache_time) < _CACHE_TTL_S:
            return self._cache

        try:
            resp = await self._client.get(
                "/data/2.5/weather",
                params={"q": city, "appid": self._api_key, "units": "metric"},
            )
            resp.raise_for_status()
            data = resp.json()

            weather = WeatherData(
                temperature_c=data["main"]["temp"],
                feels_like_c=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                wind_speed_ms=data["wind"]["speed"],
                visibility_m=data.get("visibility", 10000),
                description=data["weather"][0]["description"],
                rain_mm=data.get("rain", {}).get("1h", 0.0),
                snow_mm=data.get("snow", {}).get("1h", 0.0),
            )
            self._cache = weather
            self._cache_time = now
            return weather
        except httpx.HTTPError as e:
            logger.error("weather_fetch_failed", error=str(e))
            if self._cache:
                return self._cache
            return WeatherData(
                temperature_c=15.0,
                feels_like_c=15.0,
                humidity=50,
                wind_speed_ms=3.0,
                visibility_m=10000,
                description="unknown",
            )

    async def health_check(self) -> bool:
        """Check if OpenWeatherMap API is reachable."""
        if not self._api_key:
            return False
        try:
            resp = await self._client.get(
                "/data/2.5/weather",
                params={"q": "Paris", "appid": self._api_key, "units": "metric"},
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
