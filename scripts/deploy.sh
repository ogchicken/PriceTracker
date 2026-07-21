#!/usr/bin/env bash
# Deploy (or redeploy) the PriceTracker stack on the VPS.
#
# Run this ON the VPS from anywhere; it always operates on the repository it
# lives in. See docs/deployment.md for the full guide.
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Read a value from .env (last definition wins; surrounding quotes stripped).
read_env() { sed -n "s/^[[:space:]]*$1=//p" .env | tr -d "\"'" | tail -n 1; }

# Activate Compose profiles through the process environment. This makes profile
# selection independent of how a given Compose version treats COMPOSE_PROFILES
# inside --env-file; .env stays the single source of truth.
COMPOSE_PROFILES="$(read_env COMPOSE_PROFILES)"
export COMPOSE_PROFILES
echo "==> Compose profiles: ${COMPOSE_PROFILES:-<none>}"

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
API_PORT="$(read_env API_PORT)"
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

# When the prod profile is selected, Caddy is what terminates TLS. If it is not
# running (e.g. the profile never activated), fail loudly rather than leave the
# rest of the stack serving with no HTTPS.
case ",${COMPOSE_PROFILES}," in
  *,prod,*)
    echo "==> Verifying the caddy reverse proxy"
    caddy_id="$("${COMPOSE[@]}" ps -q caddy || true)"
    if [ -z "${caddy_id}" ] ||
      [ "$(docker inspect -f '{{.State.Running}}' "${caddy_id}" 2>/dev/null)" != "true" ]; then
      echo "ERROR: the prod profile is selected but the caddy container is not running." >&2
      echo "       Without caddy there is no HTTPS termination. Aborting." >&2
      "${COMPOSE[@]}" ps
      exit 1
    fi
    ;;
esac

DOMAIN="$(read_env DOMAIN)"
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
