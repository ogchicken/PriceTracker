# Contributing to PriceTracker

Thank you for improving PriceTracker. Keep changes focused, tested, and safe
for user data and paid-provider usage.

## Development setup

Follow the exact workflow in [README.md](README.md). You need a Clerk
**development instance** (free) for sign-in; keep the Resend key blank so email
stays non-delivering. To exercise the worker, scheduler, and full alert pipeline
without paid collections, set `PRICETRACKER_PRICE_PROVIDER=fake` (deterministic
synthetic prices, no external calls); only use the real Bright Data pipeline when
a change explicitly needs it (collections cost money). Never use production
credentials or real customer data in development.

## Workflow

1. Create a short-lived branch from the current `main`.
2. Open an issue first for architectural changes, schema rewrites, new paid
   integrations, or changes to privacy/retention behavior.
3. Make the smallest coherent change.
4. Add or update tests.
5. Run the relevant checks listed below.
6. Open a pull request describing behavior, risk, migration impact, and
   verification.

Do not commit `.env`, credentials, database dumps, generated coverage, build
output, or package-manager caches.

## Checks

Backend (start PostgreSQL first — the suite needs a real server):

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d postgres
uv run --project apps/api --with ruff ruff check apps/api
uv run --project apps/api --with ruff ruff format --check apps/api
uv run --project apps/api --with mypy mypy apps/api/app
uv run --project apps/api --directory apps/api pytest
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini check
uv run --project apps/api python apps/api/scripts/export_openapi.py --check
uv run --project apps/api python apps/api/scripts/export_marketplaces.py --check
```

Frontend:

```powershell
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web generate:api
pnpm --dir apps/web generate:marketplaces
```

Infrastructure:

```powershell
docker compose --env-file .env -f infra/compose.yaml config --quiet
```

The backend suite runs against PostgreSQL, not SQLite: the repository layer uses
`INSERT ... ON CONFLICT` and the tracking pipeline uses `FOR UPDATE SKIP LOCKED`,
so an in-memory stand-in cannot exercise any write path. It isolates itself in
its own `pricetracker_pytest` database on whichever server
`PRICETRACKER_TEST_DATABASE_URL` names (defaulting to the Compose one), creating
it on first run and resetting the schema on every run — your development
database is never touched. Tests must not call Bright Data or Resend by default;
prefer real requests through `authed_client` over reaching into private
functions.

## Database changes

- Change the ORM models and add an Alembic migration in the same pull request.
  CI enforces this with `alembic check`; run it locally against a database at
  head before pushing.
- Generate with `alembic revision --autogenerate`, then manually review both
  `upgrade()` and `downgrade()`.
- Prefer additive, backward-compatible expand/migrate/contract changes.
- Do not edit an already-deployed migration.
- Document locks, backfills, expected duration, and rollback for large tables.

## API and frontend changes

- Keep HTTP routes under `/api/v1` and preserve stable error shapes.
- Enforce ownership and limits in the API, never only in the browser.
- Update OpenAPI-facing schemas and client contract tests together.
- Supported store hosts live in exactly one place: the adapters in
  `apps/api/app/providers/adapters.py`. Add a marketplace or region there, then
  regenerate `docs/marketplaces.json` and
  `apps/web/src/lib/api/marketplaces.ts`. Never hand-edit the generated module or
  restate a domain list in `apps/web/src/lib/store-url.ts` — the browser check
  must not accept URLs the API rejects.
- Keep secrets out of client components and `NEXT_PUBLIC_*` variables.
- Meet keyboard, contrast, semantic HTML, and responsive-layout requirements.

## Pull requests

A pull request should include:

- what changed and why;
- screenshots for user-visible changes;
- tests performed;
- migration and rollback notes;
- new environment variables and deployment steps;
- privacy, security, and provider-cost impact.

Use clear commit messages in the imperative mood. Do not combine unrelated
refactors with behavior changes. All CI checks and required reviews must pass
before merge.

## Vulnerabilities and conduct

Report vulnerabilities according to [SECURITY.md](SECURITY.md), not in public
issues. Be respectful, assume good intent, and focus review comments on the
code and its user impact.

