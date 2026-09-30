#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is not installed." >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo ".env is missing. Run: cp .env.example .env && nano .env" >&2
  exit 1
fi

# Validate interpolation before changing running containers.
docker compose config >/dev/null

docker compose up -d --build

docker compose ps

echo "Deployment started. Follow logs with: docker compose logs -f web poller expiry"
