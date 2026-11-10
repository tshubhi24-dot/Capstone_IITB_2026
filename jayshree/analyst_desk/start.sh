#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required. Install Docker Desktop or Docker Engine, then retry." >&2
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "Git is required to select the image version. Install Git, then retry." >&2
    exit 1
fi

if (( $# > 1 )); then
    echo "Usage: bash ./start.sh [commit-sha]" >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop or the Docker Engine, then retry." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo ".env was not found. Copy .env.example to .env, add OPENROUTER_API_KEY, then retry." >&2
    exit 1
fi

if [[ -n "${1:-}" ]]; then
    if ! main_sha="$(git rev-parse --verify "${1}^{commit}")"; then
        echo "Could not resolve '${1}' to a commit in this checkout." >&2
        echo "Fetch the commit first, or run start.sh without an argument for the latest main image." >&2
        exit 1
    fi
    echo "Using the selected commit ${main_sha:0:7}..."
else
    if ! git fetch --quiet origin main; then
        echo "Could not fetch origin/main. Check the Git remote and network, then retry." >&2
        exit 1
    fi

    if ! main_sha="$(git rev-parse FETCH_HEAD)"; then
        echo "Could not determine the fetched main commit. Check the Git remote, then retry." >&2
        exit 1
    fi
fi

main_sha="${main_sha:0:7}"
export ANALYSTDESK_IMAGE="ghcr.io/tshubhi24-dot/analyst-desk:sha-${main_sha}"

echo "Checking for the image built from commit ${main_sha} (attempt 1 of 2)..."
if ! docker pull "$ANALYSTDESK_IMAGE"; then
    echo "The image is not available yet. Retrying once in 60 seconds..."
    sleep 60
    echo "Checking for the image built from commit ${main_sha} (attempt 2 of 2)..."
    if ! docker pull "$ANALYSTDESK_IMAGE"; then
        echo "The image for commit ${main_sha} was not available after 2 attempts." >&2
        echo "Check that the commit has a published image, then run start.sh again." >&2
        exit 1
    fi
fi

echo "Pulling service images and starting the stack with ${ANALYSTDESK_IMAGE}..."
if ! docker compose up -d --wait --wait-timeout 900; then
    echo "Startup or a health check failed. Current service status:" >&2
    docker compose ps
    echo "Review service logs with: docker compose logs" >&2
    exit 1
fi

wait_for_url() {
    local url="$1"
    local name="$2"
    local attempt

    for ((attempt = 1; attempt <= 30; attempt++)); do
        if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    echo "${name} did not become ready at ${url}." >&2
    return 1
}

echo "Checking Analyst Desk and monitoring services..."
if ! wait_for_url "http://127.0.0.1:7861/readyz" "Analyst Desk"; then
    docker compose ps
    exit 1
fi
if ! wait_for_url "http://127.0.0.1:7861/api/alerts" "In-app alerts and Prometheus connection"; then
    echo "The image may not include the current alerts API. Check the image workflow and retry." >&2
    docker compose ps
    exit 1
fi
if ! wait_for_url "http://127.0.0.1:9090/-/ready" "Prometheus"; then
    docker compose ps
    exit 1
fi
if ! wait_for_url "http://127.0.0.1:3000/api/health" "Grafana"; then
    docker compose ps
    exit 1
fi
if ! wait_for_url "http://127.0.0.1:16686/" "Jaeger"; then
    docker compose ps
    exit 1
fi

echo
echo "Analyst Desk and monitoring are ready:"
echo "  UI:         http://127.0.0.1:7861"
echo "  Prometheus: http://127.0.0.1:9090"
echo "  Grafana:    http://127.0.0.1:3000"
echo "  Jaeger:     http://127.0.0.1:16686"
if command -v open >/dev/null 2>&1; then
    if ! open "http://127.0.0.1:7861"; then
        echo "Could not open a browser automatically; visit http://127.0.0.1:7861"
    fi
elif command -v xdg-open >/dev/null 2>&1; then
    if ! xdg-open "http://127.0.0.1:7861" >/dev/null 2>&1; then
        echo "Could not open a browser automatically; visit http://127.0.0.1:7861"
    fi
fi
