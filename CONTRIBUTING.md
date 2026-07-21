# Contributing to PriceTracker

Thank you for improving PriceTracker. Keep changes focused, tested, and safe
for user data and paid-provider usage.

## Development setup

Follow the exact workflow in [README.md](README.md). You need a Clerk
**development instance** (free) for sign-in; keep the Resend key blank so
email stays non-delivering, and only run the Celery worker/scheduler when a
change explicitly needs the Bright Data pipeline (collections cost money).
Never use production credentials or real customer data in development.

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

Backend:

```powershell
uv run --project apps/api --with ruff ruff check apps/api
uv run --project apps/api --with ruff ruff format --check apps/api
uv run --project apps/api --with mypy mypy apps/api/app
uv run --project apps/api pytest
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

Frontend:

```powershell
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Infrastructure:

```powershell
docker compose --env-file .env -f infra/compose.yaml config --quiet
```

Run integration tests with isolated test databases. Tests must not call Bright
Data or Resend by default.

## Database changes

- Change the ORM models and add an Alembic migration in the same pull request.
- Generate with `alembic revision --autogenerate`, then manually review both
  `upgrade()` and `downgrade()`.
- Prefer additive, backward-compatible expand/migrate/contract changes.
- Do not edit an already-deployed migration.
- Document locks, backfills, expected duration, and rollback for large tables.

## API and frontend changes

- Keep HTTP routes under `/api/v1` and preserve stable error shapes.
- Enforce ownership and limits in the API, never only in the browser.
- Update OpenAPI-facing schemas and client contract tests together.
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

