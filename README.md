# PriceTracker

PriceTracker monitors retail product prices, records price history, and sends
user alerts when a target price is reached. It is a pnpm/uv monorepo with a
Next.js frontend, a FastAPI API, and Celery workers.

## Architecture

```text
Browser -> Next.js (apps/web) -> FastAPI (apps/api) -> PostgreSQL
                                  |      |
                                  |      +-> Redis -> Celery worker
                                  |                    |
                                  +<---------------- Bright Data
                                  |
                                  +-> Resend (price alerts)

Clerk -> Next.js session -> Clerk JWT -> FastAPI authorization
Clerk/Bright Data ---------------------> signed API webhooks
Celery beat ---------------------------> scheduled price checks
```

The API owns product, watch, price-history, alert, and webhook data. Redis is
used for Celery transport/results and short-lived coordination; PostgreSQL is
the system of record. See [docs/architecture.md](docs/architecture.md) for
trust boundaries and data flows.

## Repository layout

```text
apps/api/              FastAPI, Celery, SQLAlchemy, and Alembic
apps/web/              Next.js application
docs/                  Architecture, operations, deployment, and legal drafts
infra/compose.yaml     Local/full-stack containers
infra/render.yaml      Example hosted backend blueprint
.github/               CI, dependency updates, and ownership
```

## Prerequisites

- Git
- Node.js 22+ with Corepack
- pnpm 10+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop with Compose v2

On Windows, use PowerShell for the commands below. GNU Make is optional; the
Makefile lists equivalent commands and works from WSL or Git Bash.

## Local startup

The following is the complete host-development workflow. It runs PostgreSQL,
Redis, and Mailpit in Docker while keeping application processes on the host
for fast reloads.

1. Create local configuration:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item apps/web/.env.example apps/web/.env.local
   ```

   The checked-in defaults use `NEXT_PUBLIC_DEMO_MODE=true`,
   `PRICETRACKER_FAKE_AUTH_ENABLED=true`, and
   `PRICETRACKER_FAKE_PROVIDER_ENABLED=true`. A blank
   `PRICETRACKER_RESEND_API_KEY` selects non-delivering development email.
   Clerk, Bright Data, and Resend credentials are not required.

2. Install dependencies from the repository root:

   ```powershell
   corepack enable
   pnpm install
   uv sync --project apps/api --extra dev
   ```

3. Start development infrastructure:

   ```powershell
   docker compose --env-file .env -f infra/compose.yaml up -d postgres redis mailpit
   ```

4. Apply migrations:

   ```powershell
   uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
   ```

5. Start each process in a separate terminal:

   ```powershell
   uv run --project apps/api uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   ```powershell
   uv run --project apps/api celery -A app.workers.celery_app worker --loglevel=INFO
   ```

   ```powershell
   uv run --project apps/api celery -A app.workers.celery_app beat --loglevel=INFO
   ```

   ```powershell
   pnpm --dir apps/web dev
   ```

6. Open:

   - Web: <http://localhost:3000>
   - API documentation: <http://localhost:8000/docs>
   - Mailpit: <http://localhost:8025>

To run the entire stack from images instead, first configure `.env`, then use:

```powershell
docker compose --env-file .env -f infra/compose.yaml --profile dev up --build
```

Stop containers with:

```powershell
docker compose --env-file .env -f infra/compose.yaml --profile dev down
```

## Run for real (not demo)

Demo mode is the default. To use real Clerk sign-in, Bright Data price checks,
and Resend email alerts, follow the full guide:

**[docs/go-live.md](docs/go-live.md)**

Minimum flips after you have Clerk, Bright Data, and Resend credentials:

```dotenv
NEXT_PUBLIC_DEMO_MODE=false
PRICETRACKER_FAKE_AUTH_ENABLED=false
PRICETRACKER_FAKE_PROVIDER_ENABLED=false
CLERK_JWT_TEMPLATE_NAME=pricetracker-api
PRICETRACKER_CLERK_AUDIENCE=pricetracker-api
```

Then validate and rebuild (public Next.js flags are baked at image build time):

```powershell
python scripts/check_live_env.py
docker compose --env-file .env -f infra/compose.yaml up -d --build
```

Bright Data and Clerk webhooks cannot reach `localhost`. Expose the API with a
tunnel (Cloudflare Tunnel or ngrok) while testing locally.

## Demo and fake mode

Demo mode is intentionally explicit:

- `NEXT_PUBLIC_DEMO_MODE=true` shows deterministic sample web data.
- `PRICETRACKER_FAKE_AUTH_ENABLED=true` provides a development-only API
  identity when configured by the backend.
- `PRICETRACKER_FAKE_PROVIDER_ENABLED=true` prevents paid Bright Data
  collections.
- A blank `PRICETRACKER_RESEND_API_KEY` selects the backend's
  non-delivering logging provider in development and tests.
- Mailpit is included for local SMTP/template diagnostics at
  <http://localhost:8025>; the current backend provider uses logging or Resend
  directly and does not send through SMTP.

When `NEXT_PUBLIC_DEMO_MODE=false`, the web app does not fall back to sample
data. Missing Clerk/JWT configuration or API failures surface as errors instead.

## External service setup

### Clerk

1. Create a Clerk application and copy its publishable and secret keys to
   `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`.
2. Create a JWT template named `pricetracker-api` with
   `"aud": "pricetracker-api"` and
   `"email": "{{user.primary_email_address}}"`. Set
   `CLERK_JWT_TEMPLATE_NAME=pricetracker-api`, then set the matching issuer and
   audience in `PRICETRACKER_CLERK_ISSUER` and
   `PRICETRACKER_CLERK_AUDIENCE`. Add exact browser origins to
   `PRICETRACKER_CLERK_AUTHORIZED_PARTIES`.
3. Create a webhook ending in `/api/v1/webhooks/clerk` and subscribe only to
   events the API consumes (normally user create, update, and delete).
4. Store the signing secret as `PRICETRACKER_CLERK_WEBHOOK_SECRET`.
5. Add exact production and preview origins in Clerk and the JSON
   `PRICETRACKER_ALLOWED_ORIGINS` list.

The browser may use only the publishable key. The secret key and webhook secret
belong in backend secret storage.

### Bright Data

1. Create the required retail datasets/collectors in Bright Data.
2. Put their IDs in `PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID` and
   `PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID`.
3. Store the API token as `PRICETRACKER_BRIGHT_DATA_API_TOKEN`.
4. Configure completion callbacks to the public
   `/api/v1/webhooks/bright-data` endpoint and use the same random value for
   the provider signing configuration and
   `PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET`.
5. Set `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL` to that public endpoint, turn
   `PRICETRACKER_FAKE_PROVIDER_ENABLED=false`, and verify one low-volume
   collection before enabling schedules.

Bright Data can incur usage charges. Preserve per-user limits, retry caps, and
minimum check intervals.

### Resend

1. Verify a sending domain in Resend.
2. Create a restricted production API key and store it as
   `PRICETRACKER_RESEND_API_KEY`.
3. Set `PRICETRACKER_EMAIL_FROM` to an address on the verified domain.

Do not use a test or unverified sender for production alerts.

## Database migrations

Models and migration history must change together.

```powershell
# Generate after reviewing model changes
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "describe change"

# Review the generated upgrade and downgrade, then apply
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head

# Inspect the current revision
uv run --project apps/api alembic -c apps/api/alembic.ini current
```

Production migrations run as a one-off release/pre-deploy task, never in every
API or worker replica. Back up the database before destructive migrations.

## Quality checks

```powershell
uv run --project apps/api --with ruff ruff check apps/api
uv run --project apps/api --with ruff ruff format --check apps/api
uv run --project apps/api --with mypy mypy --config-file apps/api/pyproject.toml apps/api/app
uv run --project apps/api pytest

pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web test:e2e
pnpm --dir apps/web build

uv run --project apps/api python apps/api/scripts/export_openapi.py --check
pnpm --dir apps/web generate:api

docker compose --env-file .env -f infra/compose.yaml config --quiet
```

CI performs equivalent backend, frontend, migration, Compose, and image-build
checks. It also rejects drift in `docs/openapi.json` and the generated frontend
contract at `apps/web/src/lib/api/contract.ts`.

## API documentation

In non-production environments FastAPI serves:

- Swagger UI at `/docs`
- ReDoc at `/redoc`
- OpenAPI JSON at `/openapi.json`

All product routes are versioned under `/api/v1`. Health endpoints are
unversioned (`/healthz` and `/readyz`) so platforms can probe them without
authentication. Production documentation may be disabled; generate and publish
the OpenAPI artifact from CI instead.

## Deployment

- Frontend: Vercel, using the root `vercel.json`, or any Node container host.
- API, worker, scheduler: separate processes built from
  `apps/api/Dockerfile`.
- Data: managed PostgreSQL and Redis with private networking and TLS.
- Example backend blueprint: `infra/render.yaml`.

Follow [docs/deployment.md](docs/deployment.md) for environment promotion,
migrations, backups, and rollback. Operational expectations are in
[docs/operations.md](docs/operations.md).

For a complete account-by-account setup and launch checklist, follow
[docs/go-live.md](docs/go-live.md).

## Security and privacy

- Never expose Clerk, Bright Data, Resend, database, or webhook secrets through
  `NEXT_PUBLIC_*` variables.
- Verify JWT issuer/audience and webhook signatures before parsing trusted
  fields.
- Restrict CORS to exact origins; do not use `*` with credentials.
- Treat scraped URLs, price histories, email addresses, and alert preferences
  as user data. Minimize retention and redact logs.
- Use managed secret stores, TLS, least-privilege service credentials, private
  databases, dependency scanning, and tested backups.
- Report vulnerabilities through [SECURITY.md](SECURITY.md), not public issues.

The privacy policy and terms in `docs/` are drafts and require legal review
before launch.

## Troubleshooting

- **`pnpm` is unavailable:** run `corepack enable`, then reopen the terminal.
- **`uv` cannot find the project:** run commands from the repository root and
  keep `--project apps/api`.
- **Port already allocated:** change the corresponding `*_PORT` value in
  `.env`; keep application URLs in sync.
- **API cannot connect from a container:** host development uses `localhost`,
  while Compose overrides database and Redis hosts to `postgres` and `redis`.
  Do not put `localhost` into container-only connection strings.
- **Migrations fail on a new database:** confirm PostgreSQL is healthy with
  `docker compose --env-file .env -f infra/compose.yaml ps`, then verify
  `DATABASE_URL`.
- **Browser gets CORS errors:** add the exact web origin to the JSON
  `PRICETRACKER_ALLOWED_ORIGINS` list; schemes, ports, and hostnames must match.
- **Clerk returns 401:** compare the token's `iss` and `aud` claims with
  `PRICETRACKER_CLERK_ISSUER` and `PRICETRACKER_CLERK_AUDIENCE`, and check
  clock skew.
- **Webhook signatures fail:** use the raw request body and the endpoint's
  current secret; reverse proxies must not rewrite the body.
- **No price jobs run:** ensure Redis is reachable and both worker and scheduler
  are running. Keep fake mode enabled while diagnosing provider credentials.
- **No local email appears:** with a blank Resend key, the backend deliberately
  logs suppressed delivery instead of sending. Mailpit does not receive those
  messages unless an SMTP adapter is added.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). PriceTracker is available under the
[MIT License](LICENSE).

