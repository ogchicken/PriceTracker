# PriceTracker

PriceTracker monitors retail product prices, records price history, and sends
user alerts when a target price is reached or a tracked item comes back in
stock. It is a pnpm/uv monorepo with a
Next.js frontend, a FastAPI API, and Celery workers, deployed as a single
Docker Compose stack behind a Caddy reverse proxy.

## Architecture

```text
Browser -> Caddy (TLS) -> Next.js (apps/web) -> FastAPI (apps/api) -> PostgreSQL
                                                 |      |
                                                 |      +-> Redis -> Celery worker
                                                 |                    |
                                                 +<---------------- Bright Data
                                                 |
                                                 +-> Resend (price + stock alerts)

Clerk -> Next.js session -> Clerk JWT -> FastAPI authorization
Clerk/Bright Data ----------------------> signed API webhooks
Celery beat ----------------------------> scheduled price checks
```

The API owns product, watch, price-history, alert, and webhook data. Redis is
used for Celery transport/results and short-lived coordination; PostgreSQL is
the system of record. See [docs/architecture.md](docs/architecture.md) for
trust boundaries and data flows.

## Repository layout

```text
apps/api/              FastAPI, Celery, SQLAlchemy, and Alembic
apps/web/              Next.js application
docs/                  Architecture, operations, deployment, secrets, and legal drafts
docs/openapi.json      Generated API contract; the frontend client is generated from it
docs/marketplaces.json Generated list of supported store hosts, exported from the API adapters
infra/compose.yaml     The full Docker Compose stack (dev and production)
infra/Caddyfile        Reverse proxy and TLS termination (production profile)
scripts/deploy.sh      One-command deploy/redeploy on the VPS
.github/               CI, dependency updates, and ownership
```

## Prerequisites

- Git
- Node.js 22+ with Corepack
- pnpm 10+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop with Compose v2
- A [Clerk](https://clerk.com) application (a free development instance is
  enough for local work) — Clerk sign-in is required; there is no demo mode

On Windows, use PowerShell for the commands below. GNU Make is optional; the
Makefile lists equivalent commands and works from WSL or Git Bash.

## Local development

The host-development workflow runs PostgreSQL, Redis, and Mailpit in Docker
while keeping application processes on the host for fast reloads.

1. Create local configuration:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item apps/web/.env.example apps/web/.env.local
   ```

2. Fill in the Clerk **development instance** values in both files. You need
   at minimum:

   ```dotenv
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   CLERK_JWT_TEMPLATE_NAME=pricetracker-api
   PRICETRACKER_CLERK_ISSUER=https://YOUR_INSTANCE.clerk.accounts.dev
   PRICETRACKER_CLERK_AUDIENCE=pricetracker-api
   ```

   [docs/secrets.md](docs/secrets.md#clerk) walks through creating the Clerk
   application and the `pricetracker-api` JWT template. Bright Data and Resend
   credentials are **not** required for UI/API development; a blank
   `PRICETRACKER_RESEND_API_KEY` selects non-delivering development email.

3. Install dependencies from the repository root:

   ```powershell
   corepack enable
   pnpm install
   uv sync --project apps/api --extra dev
   ```

4. Start development infrastructure:

   ```powershell
   docker compose --env-file .env -f infra/compose.yaml up -d postgres redis mailpit
   ```

5. Apply migrations:

   ```powershell
   uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
   ```

6. Start the API and the web app in separate terminals:

   ```powershell
   uv run --project apps/api uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   ```powershell
   pnpm --dir apps/web dev
   ```

7. Open:

   - Web: <http://localhost:3000>
   - API documentation: <http://localhost:8000/docs>
   - Mailpit: <http://localhost:8025>

### The worker and scheduler in development

By default the worker performs **paid Bright Data collections**. For everyday
development you can either run the worker with the free **fake provider** (below)
or not run it at all — without a worker, new watches simply stay pending and
everything else works.

#### Fake price provider (recommended for local development)

Set `PRICETRACKER_PRICE_PROVIDER=fake` in `.env` to drive the **entire** pipeline
— scheduling, leasing, price observations, alerts, and (suppressed) emails —
with deterministic synthetic prices and **no** Bright Data credentials, HTTPS
tunnel, or external calls. Then run the worker and scheduler on the host:

```powershell
uv run --project apps/api celery -A app.workers.celery_app worker --loglevel=INFO
uv run --project apps/api celery -A app.workers.celery_app beat --loglevel=INFO
```

Prices oscillate deterministically across checks, so watches move toward their
targets and alerts fire and re-arm; alert emails appear as `email_suppressed`
log lines while the Resend key is blank. To script exact prices for specific
products, copy `apps/api/fixtures/fake_prices.example.json`, point
`PRICETRACKER_FAKE_FIXTURES_PATH` at your copy, and key entries by Amazon ASIN or
eBay item ID. The fake provider is refused in staging and production.

#### Real Bright Data pipeline

When you are specifically testing the real scraping integration, fill in the
Bright Data variables (see [docs/secrets.md](docs/secrets.md#bright-data)),
expose your local API with an HTTPS tunnel (Bright Data cannot call
`localhost`):

```powershell
cloudflared tunnel --url http://localhost:8000
```

set `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL=https://TUNNEL_DOMAIN/api/v1/webhooks/bright-data`,
then run:

```powershell
uv run --project apps/api celery -A app.workers.celery_app worker --loglevel=INFO
uv run --project apps/api celery -A app.workers.celery_app beat --loglevel=INFO
```

Start with a single test product and configure Bright Data budget alerts.

## Database migrations

Models and migration history must change together.

```powershell
# Generate after reviewing model changes
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "describe change"

# Review the generated upgrade and downgrade, then apply
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head

# Inspect the current revision
uv run --project apps/api alembic -c apps/api/alembic.ini current

# Fail if the models and the migration history have drifted apart
uv run --project apps/api alembic -c apps/api/alembic.ini check
```

`alembic check` is what enforces the rule above: it compares the ORM metadata
against a database already migrated to head and fails when a model change has no
matching migration. CI runs it on every pull request.

In production, migrations run as a dedicated one-shot Compose service
(`migrate`) invoked by `scripts/deploy.sh` before the stack restarts — never in
every API or worker replica. Back up the database before destructive
migrations.

## Quality checks

The backend suite runs against a real PostgreSQL server, so start the
development infrastructure first:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d postgres
```

It uses its own `pricetracker_pytest` database on that server, creating it on
first run and resetting the schema each run, so it never touches your
development data. Point `PRICETRACKER_TEST_DATABASE_URL` at a different server if
you prefer.

```powershell
uv run --project apps/api --with ruff ruff check apps/api
uv run --project apps/api --with ruff ruff format --check apps/api
uv run --project apps/api --with mypy mypy --config-file apps/api/pyproject.toml apps/api/app
uv run --project apps/api --directory apps/api pytest

pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web test:e2e
pnpm --dir apps/web build

uv run --project apps/api alembic -c apps/api/alembic.ini check
uv run --project apps/api python apps/api/scripts/export_openapi.py --check
uv run --project apps/api python apps/api/scripts/export_marketplaces.py --check
pnpm --dir apps/web generate:api
pnpm --dir apps/web generate:marketplaces

docker compose --env-file .env -f infra/compose.yaml config --quiet
```

`pytest` needs `--directory apps/api`: it discovers its configuration from the
working directory upwards, and there is none at the repository root, so running
it from there silently disables `asyncio_mode` and skips every async test.

CI performs equivalent backend, frontend, migration, Compose, and image-build
checks. It also rejects model/migration drift and drift in `docs/openapi.json`,
`docs/marketplaces.json`, and the generated frontend modules at
`apps/web/src/lib/api/contract.ts` and `apps/web/src/lib/api/marketplaces.ts`.

## API documentation

In non-production environments FastAPI serves:

- Swagger UI at `/docs`
- ReDoc at `/redoc`
- OpenAPI JSON at `/openapi.json`

All product routes are versioned under `/api/v1`. Health endpoints are
unversioned (`/healthz` and `/readyz`) so monitors can probe them without
authentication.

## Deployment

The production deployment is a single VPS running the whole stack with Docker
Compose:

- **Caddy** terminates TLS for your domain (automatic Let's Encrypt) and is
  the only service exposed to the internet.
- **Next.js web**, **FastAPI api**, **Celery worker**, and **beat scheduler**
  containers plus **PostgreSQL** and **Redis** run on the internal network.
- Redeploying is one command on the VPS: `./scripts/deploy.sh` (or from your
  machine: `make deploy VPS_HOST=user@your-vps`).

Follow the guides:

- **[docs/deployment.md](docs/deployment.md)** — step-by-step VPS setup, first
  deploy, redeploys, backups, and rollback.
- **[docs/secrets.md](docs/secrets.md)** — how to obtain every value in
  `.env` (Clerk, Bright Data, Resend, self-generated secrets).
- [docs/operations.md](docs/operations.md) — operating the stack after launch.

## Security and privacy

- Never expose Clerk, Bright Data, Resend, database, or webhook secrets through
  `NEXT_PUBLIC_*` variables.
- Verify JWT issuer/audience and webhook signatures before parsing trusted
  fields.
- Restrict CORS to exact origins; do not use `*` with credentials.
- Treat scraped URLs, price histories, email addresses, and alert preferences
  as user data. Minimize retention and redact logs.
- Keep secrets in the VPS `.env` (mode 600) only, use TLS everywhere, keep
  PostgreSQL/Redis bound to loopback, and test backups.
- Report vulnerabilities through [SECURITY.md](SECURITY.md), not public issues.

The privacy policy and terms in `docs/` are drafts and require legal review
before launch.

## Troubleshooting

- **`pnpm` is unavailable:** run `corepack enable`, then reopen the terminal.
- **`uv` cannot find the project:** run commands from the repository root and
  keep `--project apps/api`.
- **Port already allocated:** change the corresponding `*_PORT` value in
  `.env`; keep application URLs in sync.
- **The web app throws `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is required`:**
  fill the Clerk keys in `apps/web/.env.local` (host dev) or `.env` (Compose);
  there is no demo fallback.
- **API cannot connect from a container:** host development reaches PostgreSQL
  and Redis at `127.0.0.1`, while Compose overrides those hosts to `postgres`
  and `redis`. Do not put a loopback address into container-only connection
  strings.
- **Every database or Redis call takes about two extra seconds:** the
  connection URL is using `localhost`. Compose publishes these ports on IPv4
  only, and resolving `localhost` tries `::1` first, so each new connection
  stalls on a refused IPv6 attempt before falling back — most visible on
  Windows. Use `127.0.0.1`, as `.env.example` does.
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
- **No price jobs run:** ensure Redis is reachable and both worker and
  scheduler are running, and that the Bright Data credentials and webhook URL
  are configured.
- **No local email appears:** with a blank Resend key, the backend deliberately
  logs suppressed delivery instead of sending. Mailpit does not receive those
  messages unless an SMTP adapter is added.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). PriceTracker is available under the
[MIT License](LICENSE).
