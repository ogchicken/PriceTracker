#!/usr/bin/env bash
# Deploy (or redeploy) the PriceTracker stack on the VPS.
#
# Run this ON the VPS from anywhere; it always operates on the repository it
# lives in. See docs/deployment.md for the full guide.
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

COMPOSE=(docker compose --env-file .env -f infra/compose.yaml)

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Validating .env"
python3 scripts/check_live_env.py --env-file .env

echo "==> Building images"
"${COMPOSE[@]}" build

echo "==> Running database migrations"
"${COMPOSE[@]}" run --rm migrate

echo "==> Starting services"
"${COMPOSE[@]}" up -d --remove-orphans

echo "==> Waiting for the API to become ready"
API_PORT="$(sed -n 's/^API_PORT=//p' .env | tr -d '"' | tail -n 1)"
API_PORT="${API_PORT:-8000}"
ready=0
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${API_PORT}/readyz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [ "${ready}" != 1 ]; then
  echo "ERROR: the API did not become ready; recent logs follow." >&2
  "${COMPOSE[@]}" ps
  "${COMPOSE[@]}" logs --tail=100 api
  exit 1
fi

DOMAIN="$(sed -n 's/^DOMAIN=//p' .env | tr -d '"' | tail -n 1)"
if [ -n "${DOMAIN}" ] && [ "${DOMAIN}" != "localhost" ]; then
  if curl -fsS --max-time 15 "https://${DOMAIN}/healthz" >/dev/null 2>&1; then
    echo "==> Public health check passed: https://${DOMAIN}/healthz"
  else
    echo "WARN: https://${DOMAIN}/healthz is not reachable yet." >&2
    echo "      On a first deploy this usually means DNS or the TLS certificate" >&2
    echo "      is still propagating; watch: docker compose --env-file .env -f infra/compose.yaml logs -f caddy" >&2
  fi
fi

echo "==> Pruning dangling images"
docker image prune -f

echo "Deploy complete."
