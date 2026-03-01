"""Extract Points of Interest from Overpass API and load into DuckDB.

Usage: python scripts/extract_pois.py
"""

import json
import uuid

import duckdb
import httpx
import yaml

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def load_city_config() -> dict:
    """Load city configuration from YAML."""
    with open("config/city.yaml") as f:
        return yaml.safe_load(f)


def build_overpass_query(bbox: dict, categories: dict) -> str:
    """Build Overpass QL query for all POI categories.

    Args:
        bbox: Bounding box with south, west, north, east.
        categories: Dict of category name -> list of OSM tag filters.

    Returns:
        Overpass QL query string.
    """
    bb = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
    parts = ["[out:json][timeout:60];", "("]

    for _category, tags in categories.items():
        for tag in tags:
            key, value = tag.split("=")
            parts.append(f'  node["{key}"="{value}"]({bb});')
            parts.append(f'  way["{key}"="{value}"]({bb});')

    parts.append(");")
    parts.append("out center;")
    return "\n".join(parts)


def fetch_pois(query: str) -> list[dict]:
    """Execute Overpass query and return parsed elements."""
    resp = httpx.post(OVERPASS_URL, data={"data": query}, timeout=120.0)
    resp.raise_for_status()
    data = resp.json()
    return data.get("elements", [])


def categorize_element(tags: dict, categories: dict) -> str:
    """Determine category for an OSM element based on its tags."""
    for category, cat_tags in categories.items():
        for cat_tag in cat_tags:
            key, value = cat_tag.split("=")
            if tags.get(key) == value:
                return category
    return "commerce"


def main() -> None:
    config = load_city_config()
    city = config["city"]
    categories = config["poi_categories"]

    print(f"Extracting POIs for {city['name']}...")
    query = build_overpass_query(city["bbox"], categories)
    elements = fetch_pois(query)
    print(f"Fetched {len(elements)} OSM elements")

    # Connect to DuckDB
    conn = duckdb.connect("data/game.duckdb")
    conn.execute("INSTALL spatial; LOAD spatial;")
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

    inserted = 0
    for el in elements:
        tags = el.get("tags", {})
        # Get coordinates (node: lat/lon, way: center.lat/center.lon)
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue

        name = tags.get("name", tags.get("amenity", tags.get("shop", "unnamed")))
        category = categorize_element(tags, categories)
        poi_id = f"poi_{el['type']}_{el['id']}"

        conn.execute(
            """
            INSERT OR REPLACE INTO pois (poi_id, name, category, lat, lon, osm_tags, geom)
            VALUES (?, ?, ?, ?, ?, ?, ST_Point(?, ?))
            """,
            [poi_id, name, category, lat, lon, json.dumps(tags), lon, lat],
        )
        inserted += 1

    conn.close()
    print(f"Inserted {inserted} POIs into DuckDB")


if __name__ == "__main__":
    main()
