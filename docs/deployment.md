# Deployment

This guide is provider-neutral. The recommended split is Vercel for the
Next.js frontend and a container platform for the API, workers, and scheduler,
with managed PostgreSQL and Redis. `infra/render.yaml` is an example, not a
complete production policy.

## Production topology

- Deploy `apps/web` to Vercel or run `apps/web/Dockerfile`.
- Build one immutable backend image from `apps/api/Dockerfile`.
- Run that image as three process types:
  - API: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
  - worker: `celery -A app.workers.celery_app worker --loglevel=INFO`
  - scheduler: `celery -A app.workers.celery_app beat --loglevel=INFO --pidfile=/tmp/celerybeat.pid --schedule=/tmp/celerybeat-schedule`
- Use managed PostgreSQL and Redis on private networks with encryption in
  transit and at rest.
- Run exactly one scheduler per environment.

Pin deployed images by digest or commit SHA. Do not deploy from mutable
`latest` tags.

## Environment configuration

Start from `.env.example`, but store values in each platform's encrypted
environment settings rather than uploading an `.env` file.

Frontend build/runtime values:

- `API_BASE_URL` (server only)
- `NEXT_PUBLIC_DEMO_MODE=false`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `CLERK_JWT_TEMPLATE_NAME=pricetracker-api`

Backend values:

- runtime: `PRICETRACKER_ENVIRONMENT=production`,
  process-specific `PRICETRACKER_SERVICE_ROLE`, `PRICETRACKER_DEBUG=false`,
  `PRICETRACKER_LOG_LEVEL`;
- data: `PRICETRACKER_DATABASE_URL`, `PRICETRACKER_REDIS_URL`,
  `PRICETRACKER_CELERY_BROKER_URL`,
  `PRICETRACKER_CELERY_RESULT_BACKEND`;
- URLs/security: `PRICETRACKER_FRONTEND_BASE_URL` and the exact JSON
  `PRICETRACKER_ALLOWED_ORIGINS` list;
- Clerk: `PRICETRACKER_CLERK_ISSUER`,
  `PRICETRACKER_CLERK_AUDIENCE`,
  `PRICETRACKER_CLERK_AUTHORIZED_PARTIES`, and
  `PRICETRACKER_CLERK_WEBHOOK_SECRET`;
- Bright Data: `PRICETRACKER_FAKE_PROVIDER_ENABLED=false`,
  `PRICETRACKER_BRIGHT_DATA_API_TOKEN`, Amazon/eBay dataset IDs, and webhook
  URL/secret;
- email: `PRICETRACKER_RESEND_API_KEY` and `PRICETRACKER_EMAIL_FROM`;
- limits and observability values from `.env.example`.

Use different credentials, Clerk instances, databases, Redis instances, and
webhook endpoints for preview/staging and production. Preview environments
should normally retain Bright Data fake mode and non-delivery email.

## Vercel frontend

The root `vercel.json` supports importing the repository root as a Vercel
project. It installs the workspace and builds `apps/web`.

1. Import the repository and keep the project root at the repository root.
2. Select pnpm and Node.js 22.
3. Add frontend variables separately for Preview and Production.
4. Set server-only `API_BASE_URL` to the corresponding public API origin and
   set `NEXT_PUBLIC_DEMO_MODE=false`.
5. Add each Vercel origin to Clerk and backend
   `PRICETRACKER_ALLOWED_ORIGINS`.
6. Deploy a preview and verify authentication and API calls before promoting.

`NEXT_PUBLIC_*` values are embedded at build time. Changing them requires a new
frontend deployment. Never place secret keys in that namespace.

Alternatively, set Vercel's project root to `apps/web` and remove/override the
root build settings in the Vercel dashboard.

## Container backend

The backend image must include application code, locked dependencies, and
Alembic migrations. The API health endpoints are:

- `/healthz` for process liveness;
- `/readyz` for dependency readiness.

Expose only the API. Worker and scheduler processes require outbound access to
PostgreSQL, Redis, Bright Data, Resend, and observability endpoints but do not
need public ingress.

Recommended process lifecycle:

1. Stop accepting new work on termination.
2. Allow API requests and Celery tasks a bounded grace period.
3. Terminate after the platform timeout.
4. Retry only idempotent tasks.

Scale API replicas on request latency/concurrency. Scale workers on queue age
and depth while enforcing provider-spend and database-connection ceilings.
Keep scheduler replicas fixed at one.

## Release procedure

1. Confirm CI is green and the image corresponds to the intended commit.
2. Review migrations for locks, rewrites, backfills, and downgrade behavior.
3. Take or verify a recoverable database backup for destructive changes.
4. Build and push the image once.
5. Run `alembic upgrade head` as a one-off pre-deploy/release command.
6. Deploy API replicas and wait for readiness.
7. Deploy workers.
8. Replace the single scheduler.
9. Deploy the web app.
10. Verify health, authentication, one synthetic watch, queue age, provider
    usage, and email delivery.

Do not run migrations automatically in every API/worker startup command;
concurrent migration runners can race and slow rollouts.

## Migration strategy

Prefer expand/migrate/contract:

1. **Expand:** add nullable columns, new tables, or compatible indexes.
2. **Migrate:** deploy code that reads/writes both forms and backfill in
   resumable batches.
3. **Contract:** after all instances use the new form, remove old fields in a
   later release.

Create large PostgreSQL indexes concurrently where migration tooling and
transaction boundaries support it. Set and test statement/lock timeouts. Never
edit migration files that have reached a shared environment.

## Backups and restore

Use provider-managed point-in-time recovery for PostgreSQL and retain periodic
independent snapshots according to business recovery objectives. At minimum:

- monitor backup completion and retention;
- encrypt backups and restrict restore permissions;
- document the recovery point objective (RPO) and recovery time objective
  (RTO);
- perform a restore drill into an isolated environment at least quarterly;
- verify schema revision, row counts, application login, and representative
  price history after restore.

Redis is not the business-record backup. After Redis loss, restore queue
service and run a controlled reconciliation that re-enqueues due database
records.

Before a planned destructive migration, record the backup identifier and test
that it is restorable. Database exports containing user data must follow the
same retention and access controls as production.

## Rollback

For an application regression:

1. Pause the scheduler if new jobs could worsen the issue.
2. Redeploy the previous immutable API/worker image.
3. Restore the previous frontend deployment.
4. Reconcile queued/running jobs and verify idempotency records.

Prefer a forward-fix for schema changes. Run `alembic downgrade` only when the
reviewed downgrade is data-preserving, no newer application writes depend on
the schema, and the migration owner has approved it. Otherwise deploy
compatibility code, restore from backup if data is corrupted, and complete a
forward migration.

Credential or signing-key rollback means rotation, not restoration of an
exposed value.

## Domains and webhooks

Use HTTPS everywhere. Configure:

- Clerk webhook: `https://api.example.com/api/v1/webhooks/clerk`
- Bright Data webhook and `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL`:
  `https://api.example.com/api/v1/webhooks/bright-data`
- frontend server API URL: `API_BASE_URL=https://api.example.com`
- backend origins:
  `PRICETRACKER_FRONTEND_BASE_URL=https://app.example.com` and an exact JSON
  `PRICETRACKER_ALLOWED_ORIGINS` allowlist.

Rotate webhook secrets during a controlled overlap window if the provider
supports multiple active secrets. Verify signatures before returning success.

## Render example

`infra/render.yaml` illustrates managed PostgreSQL/Redis plus API, worker, and
scheduler services. Before using it:

- replace placeholder plans/regions and secret values;
- confirm the current Render Blueprint schema and PostgreSQL version support;
- confirm Render linked `PRICETRACKER_DATABASE_URL` to the managed database;
  the application normalizes Render's PostgreSQL scheme to `asyncpg`;
- configure a one-off migration/pre-deploy command;
- set public `API_URL`, `WEB_URL`, webhook URLs, and CORS origins;
- connect the web project in Vercel;
- add alerts, backups, autoscaling limits, and a custom API domain.

The complete account setup, environment values, webhook sequence, and
verification checklist are in [go-live.md](go-live.md).

