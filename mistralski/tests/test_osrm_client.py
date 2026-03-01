"""Tests for OSRM routing client."""

import pytest
import respx
from httpx import Response

from src.clients.osrm import OSRMClient, _decode_polyline
from src.core.config import Settings
from src.core.exceptions import RoutingError


@pytest.fixture
def settings() -> Settings:
    return Settings(osrm_base_url="http://test-osrm:5000")


@pytest.fixture
def client(settings: Settings) -> OSRMClient:
    return OSRMClient(settings)


ROUTE_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 1234.5,
            "duration": 890.2,
            "geometry": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
        }
    ],
}

NEAREST_RESPONSE = {
    "code": "Ok",
    "waypoints": [
        {
            "location": [2.3522, 48.8566],
            "distance": 5.2,
            "name": "Rue de Rivoli",
        }
    ],
}


@respx.mock
@pytest.mark.asyncio
async def test_route_success(client: OSRMClient) -> None:
    respx.get("http://test-osrm:5000/route/v1/foot/2.3522,48.8566;2.36,48.86").mock(
        return_value=Response(200, json=ROUTE_RESPONSE)
    )
    result = await client.route((48.8566, 2.3522), (48.86, 2.36))
    assert result.distance_m == 1234.5
    assert result.duration_s == 890.2
    assert len(result.geometry) > 0


@respx.mock
@pytest.mark.asyncio
async def test_route_no_route(client: OSRMClient) -> None:
    respx.get("http://test-osrm:5000/route/v1/foot/2.3522,48.8566;2.36,48.86").mock(
        return_value=Response(200, json={"code": "NoRoute", "routes": []})
    )
    with pytest.raises(RoutingError):
        await client.route((48.8566, 2.3522), (48.86, 2.36))


@respx.mock
@pytest.mark.asyncio
async def test_nearest_success(client: OSRMClient) -> None:
    respx.get("http://test-osrm:5000/nearest/v1/foot/2.3522,48.8566").mock(
        return_value=Response(200, json=NEAREST_RESPONSE)
    )
    result = await client.nearest((48.8566, 2.3522))
    assert result.lat == 48.8566
    assert result.lon == 2.3522
    assert result.name == "Rue de Rivoli"


def test_decode_polyline() -> None:
    # Known encoded polyline
    coords = _decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(coords) == 3
    assert abs(coords[0][0] - 38.5) < 0.1
    assert abs(coords[0][1] - (-120.2)) < 0.1


@respx.mock
@pytest.mark.asyncio
async def test_health_check(client: OSRMClient) -> None:
    respx.get("http://test-osrm:5000/route/v1/foot/2.3522,48.8566;2.3600,48.8600").mock(
        return_value=Response(200, json=ROUTE_RESPONSE)
    )
    assert await client.health_check() is True
