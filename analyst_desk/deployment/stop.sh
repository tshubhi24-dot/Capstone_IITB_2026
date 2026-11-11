#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required. Install Docker Desktop or Docker Engine, then retry." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop or the Docker Engine, then retry." >&2
    exit 1
fi

if ! docker compose --project-directory . -f deployment/compose.yaml down; then
    echo "Could not stop the Analyst Desk services. Check Docker Compose output above." >&2
    exit 1
fi

echo "Analyst Desk services stopped. Persistent data volumes were kept."
