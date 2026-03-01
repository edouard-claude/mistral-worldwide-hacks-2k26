#!/usr/bin/env bash
# Download and prepare OSRM data for Ile-de-France (Paris region)
# Usage: bash scripts/setup_osrm.sh

set -euo pipefail

DATA_DIR="data/paris"
PBF_URL="https://download.geofabrik.de/europe/france/ile-de-france-latest.osm.pbf"
PBF_FILE="$DATA_DIR/ile-de-france-latest.osm.pbf"
OSRM_IMAGE="osrm/osrm-backend:latest"

echo "=== OSRM Setup for Paris ==="

# Create data directory
mkdir -p "$DATA_DIR"

# Download PBF if not present
if [ ! -f "$PBF_FILE" ]; then
    echo "[1/4] Downloading Ile-de-France OSM extract..."
    curl -L -o "$PBF_FILE" "$PBF_URL"
else
    echo "[1/4] PBF file already exists, skipping download."
fi

# Extract (foot profile for pedestrian routing)
echo "[2/4] Extracting with foot profile..."
docker run --rm -v "$(pwd)/$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-extract -p /opt/foot.lua /data/ile-de-france-latest.osm.pbf

# Partition (MLD algorithm)
echo "[3/4] Partitioning..."
docker run --rm -v "$(pwd)/$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-partition /data/ile-de-france-latest.osrm

# Customize
echo "[4/4] Customizing..."
docker run --rm -v "$(pwd)/$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-customize /data/ile-de-france-latest.osrm

echo ""
echo "=== OSRM data ready! ==="
echo "Start with: docker compose up osrm"
