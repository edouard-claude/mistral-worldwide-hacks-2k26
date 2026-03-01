"""OSRM routing client for pedestrian and car routing."""

from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from src.core.config import Settings
from src.core.exceptions import RoutingError

logger = structlog.get_logger(__name__)


class RouteResult(BaseModel):
    """Result from an OSRM route query."""

    distance_m: float
    duration_s: float
    geometry: list[tuple[float, float]]  # list of (lat, lon)


class NearestResult(BaseModel):
    """Result from an OSRM nearest query."""

    lat: float
    lon: float
    distance_m: float
    name: str = ""


def _decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Decode Google polyline encoding to list of (lat, lon)."""
    coordinates: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lon = 0
    factor = 10**precision

    while index < len(encoded):
        for is_lon in (False, True):
            shift = 0
            result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += delta
            else:
                lat += delta
            if is_lon:
                coordinates.append((lat / factor, lon / factor))

    return coordinates


class OSRMClient:
    """Client for OSRM routing engine."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.osrm_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def route(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        profile: str = "foot",
    ) -> RouteResult:
        """Calculate route between two points.

        Args:
            origin: (lat, lon) of start point.
            dest: (lat, lon) of end point.
            profile: Routing profile ('foot' or 'car').

        Returns:
            RouteResult with distance, duration, geometry.

        Raises:
            RoutingError: On routing failure.
        """
        # OSRM expects lon,lat order
        coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
        try:
            resp = await self._client.get(
                f"/route/v1/{profile}/{coords}",
                params={"overview": "full", "geometries": "polyline"},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as e:
            raise RoutingError(f"OSRM route failed: {e}") from e

        if data.get("code") != "Ok" or not data.get("routes"):
            raise RoutingError(f"OSRM returned no route: {data.get('code')}")

        route = data["routes"][0]
        geometry = _decode_polyline(route["geometry"])

        return RouteResult(
            distance_m=route["distance"],
            duration_s=route["duration"],
            geometry=geometry,
        )

    async def nearest(
        self,
        point: tuple[float, float],
        profile: str = "foot",
    ) -> NearestResult:
        """Snap a point to the nearest road network node.

        Args:
            point: (lat, lon) to snap.
            profile: Routing profile.

        Returns:
            NearestResult with snapped coordinates.

        Raises:
            RoutingError: On failure.
        """
        coord = f"{point[1]},{point[0]}"
        try:
            resp = await self._client.get(f"/nearest/v1/{profile}/{coord}")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as e:
            raise RoutingError(f"OSRM nearest failed: {e}") from e

        if data.get("code") != "Ok" or not data.get("waypoints"):
            raise RoutingError(f"OSRM nearest failed: {data.get('code')}")

        wp = data["waypoints"][0]
        return NearestResult(
            lat=wp["location"][1],
            lon=wp["location"][0],
            distance_m=wp["distance"],
            name=wp.get("name", ""),
        )

    async def health_check(self) -> bool:
        """Check if OSRM server is reachable."""
        try:
            resp = await self._client.get("/route/v1/foot/2.3522,48.8566;2.3600,48.8600")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
