# Operations

## Service objectives

Define targets from product requirements and measured baselines before public
launch. At minimum, track API availability/latency, schedule delay, collection
freshness, and alert-delivery success. Exclude planned maintenance explicitly
and alert on error-budget burn rather than isolated failures.

Suggested initial indicators:

- successful non-health API requests and p50/p95/p99 latency;
- age of the oldest due watch not yet claimed;
- age and depth of each Celery queue;
- time from scheduled check to persisted observation;
- provider collection success, timeout, malformed-result, and retry rates;
- time from alert-triggering observation to accepted email;
- webhook signature failures, duplicate events, and processing lag;
- database connection saturation, transaction latency, locks, storage, and
  replication/backup health;
- Redis memory, evictions, rejected connections, and persistence health.

## Telemetry

Emit structured JSON logs in production with timestamp, level, service,
environment, request/task ID, route/task name, and duration. Propagate a
correlation ID from API/webhooks into Celery tasks. Read logs on the VPS with
`docker compose --env-file .env -f infra/compose.yaml logs [service]`.

Never log bearer tokens, cookies, webhook signatures, secret values, full
email addresses, or raw provider payloads. Hash or redact user and product
identifiers where full values are unnecessary.

Prometheus metrics are exposed at `/metrics`, which is deliberately not routed
through Caddy; scrape or inspect it on the VPS via
`curl http://127.0.0.1:8000/metrics`. Error-reporting (Sentry) and
OpenTelemetry exporters are not currently wired into the codebase; if added,
keep trace sampling low by default and scrub request bodies and headers before
export.

## Health and alerting

- `/healthz` checks only that the API process can serve.
- `/readyz` checks dependencies required to accept traffic.
- Celery worker health verifies a targeted worker response, not merely a
  running PID.
- Scheduler health verifies that the singleton emits a recent heartbeat.

Page immediately for sustained API unavailability, inability to write to
PostgreSQL, runaway provider spend, exposed credentials, or cross-user data
risk. Create actionable non-page alerts for queue delay, increased provider
errors, email failures, backup failures, disk growth, and impending limits.
Every alert should link to a runbook and name its owner.

## Runbook: API errors or latency

1. Check whether the issue is global, route-specific, or tied to one release.
2. Compare request latency with PostgreSQL pool wait, query time, Redis
   latency, and external-call latency.
3. Check current deployment health and error traces using redacted IDs.
4. If a new release correlates and schema is compatible, roll back the image.
5. If load is legitimate, scale only after confirming database and downstream
   capacity.
6. Preserve evidence and record the timeline.

Do not mask database saturation by adding API replicas; that increases
connection pressure.

## Runbook: queue backlog or stale prices

1. Measure oldest-message age and split backlog by queue/task.
2. Confirm Redis health and active worker heartbeats.
3. Check failed/retried task rates and database/provider latency.
4. Pause the scheduler if it is adding work faster than safe throughput.
5. Scale workers within database, Redis, and provider-budget limits.
6. Quarantine poison messages and replay only after correcting idempotency.
7. Reconcile due watches from PostgreSQL after recovery.

Never purge queues without recording affected jobs and having a database-based
reconciliation plan.

While Redis is unavailable, `POST /api/v1/watches` returns 503 by design — the
creation rate limiter fails closed to protect provider spend — so treat those
503s as expected during a Redis outage, not as a separate API fault.

## Runbook: scheduler missing or duplicated checks

1. Confirm exactly one scheduler instance and a recent scheduler heartbeat.
2. Inspect due-watch selection, timezone handling, and lock expiry.
3. Check collection-job deduplication keys before replaying.
4. Start one scheduler if absent; stop extras if duplicated.
5. Enqueue a bounded reconciliation batch rather than all watches at once.

All schedule timestamps are UTC. A duplicate schedule tick must not purchase a
duplicate collection.

## Runbook: Bright Data failures

1. Check provider status, quota, balance, dataset configuration, and response
   codes.
2. Compare failures by retailer/dataset and recent application release.
3. Verify callback URL reachability and raw-body signature validation.
4. Stop or sharply reduce new collections for authentication, quota, schema,
   or runaway-cost errors.
5. Retry transient failures with capped exponential backoff and jitter.
6. Store a redacted malformed sample in restricted debugging storage, not
   normal logs.
7. In development, either stop the worker/scheduler while provider credentials
   are broken, or switch to the fake price provider
   (`PRICETRACKER_PRICE_PROVIDER=fake`), which serves deterministic synthetic
   prices without calling Bright Data and is refused in staging and production.

## Runbook: webhook backlog or signature failures

1. Compare provider delivery logs with API response codes and ingress logs.
2. Verify the deployed endpoint, timestamp tolerance, and current secret.
3. Ensure proxies have not altered the raw body.
4. Check duplicate-event storage and queue availability.
5. Rotate a suspected secret and investigate access logs.
6. Ask the provider to replay only the known missing event range.

Return success quickly only after authenticity and durable deduplication have
been established.

## Runbook: Resend delivery failures

1. Check Resend status, API response, domain verification, suppression, and
   sender alignment.
2. Distinguish temporary provider failures from permanent recipient failures.
3. Retry temporary failures using the alert idempotency key.
4. Suppress repeated permanent failures and expose a user-remediation path.
5. Confirm delivery records remain linked to the triggering observation.

Never resend all historical alerts after an outage.

## Runbook: database incident

1. Stop the scheduler and pause workers if writes could worsen corruption or
   contention.
2. Check managed-database health, connection limits, locks, storage, and
   replica lag.
3. Shed nonessential traffic and reduce connection pools if saturated.
4. For data loss/corruption, declare an incident and identify the recovery
   point before restoring into an isolated environment.
5. Follow `docs/deployment.md` for restore validation and controlled cutover.
6. Reconcile Redis queues against restored PostgreSQL state.

## Runbook: suspected credential or data exposure

1. Restrict access and preserve audit evidence.
2. Revoke and rotate the affected key, token, webhook secret, or database
   credential.
3. Invalidate sessions when Clerk/session material may be affected.
4. Determine scope using provider and platform audit logs without spreading
   sensitive data.
5. Follow the incident notification process and applicable legal obligations.
6. Add a regression control and document the incident.

Do not delay rotation while attempting to remove a leaked secret from Git
history.

## Cost controls

Bright Data and email are variable-cost dependencies. Enforce controls at the
API and worker, not only in UI:

- a minimum `PRICETRACKER_TRACKING_INTERVAL_HOURS` plus randomized
  `PRICETRACKER_TRACKING_JITTER_MINUTES`;
- product leases bounded by `PRICETRACKER_PRODUCT_LEASE_MINUTES`;
- one active watch per intended user/product/retailer combination;
- per-user ceilings on active watches (`PRICETRACKER_MAX_ACTIVE_WATCHES_PER_USER`)
  and hourly watch creation (`PRICETRACKER_WATCH_CREATE_RATE_LIMIT_PER_HOUR`); the
  creation limiter fails closed (returns 503) when Redis is unavailable, so an
  outage cannot become an unlimited-create bypass;
- collection deduplication and provider idempotency keys;
- stale-job detection, `PRICETRACKER_PROVIDER_MAX_ATTEMPTS`, and bounded worker
  concurrency;
- per-user, per-retailer, and global hourly/daily collection ceilings;
- a circuit breaker for provider auth, quota, schema, and elevated error rates;
- mocked provider transports in tests and non-delivering email (blank Resend
  key) in routine development, so neither spends money;
- provider budget alerts at multiple thresholds and a hard operational stop;
- dashboards for spend per successful observation and per active paid user.

Increasing worker replicas must not automatically increase the global provider
budget. Require an explicit configuration change and review for higher caps.

## Routine operations

Daily checks should include active incidents, error-budget burn, oldest queue
age, provider spend/errors, email failures, and backup status. Weekly reviews
should include dependency alerts, database/Redis capacity, retry hot spots, and
cost per successful check. Quarterly work should include restore drills,
credential rotation where supported, retention review, incident simulations,
and access review.

