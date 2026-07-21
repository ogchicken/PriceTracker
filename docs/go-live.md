# Go Live

This runbook covers two real-data setups:

1. a local installation using real Clerk, Bright Data, and Resend accounts;
2. a hosted production installation using Render for backend services and
   Vercel for the frontend.

Real mode performs paid Bright Data collections and can send real email. Start
with one test product and configure provider budget alerts before adding users.

## Quick checklist

| Step | What you need |
| --- | --- |
| 1 | Clerk app + JWT template named `pricetracker-api` with `"aud": "pricetracker-api"` |
| 2 | Bright Data Amazon + eBay dataset IDs and API token |
| 3 | Resend verified domain + API key |
| 4 | Public HTTPS tunnel to local API (or a hosted API domain) |
| 5 | `.env` with demo/fake flags set to `false` |
| 6 | `python scripts/check_live_env.py` then rebuild Compose |

```powershell
python scripts/check_live_env.py
docker compose --env-file .env -f infra/compose.yaml up -d --build
docker compose --env-file .env -f infra/compose.yaml ps
```

## 1. Create the external accounts

You need:

- a Clerk application for authentication;
- a Bright Data account with compatible Amazon product and eBay product
  datasets;
- a Resend account with a verified sending domain;
- for production, a Git provider repository, a Vercel account, and a Render
  account.

Keep development and production credentials separate.

## 2. Configure Clerk

### Create the JWT template

In Clerk Dashboard, open **JWT templates** and create a blank template:

- Template name: `pricetracker-api`
- Token lifetime: 60 seconds
- Allowed clock skew: 5 seconds
- Claims:

```json
{
  "aud": "pricetracker-api",
  "email": "{{user.primary_email_address}}"
}
```

The template name must match `CLERK_JWT_TEMPLATE_NAME`, and the `aud` value
must match `PRICETRACKER_CLERK_AUDIENCE`.

### Record Clerk values

From Clerk Dashboard, record:

- publishable key (`pk_...`);
- secret key (`sk_...`);
- Frontend API/issuer URL, such as
  `https://example-name.clerk.accounts.dev`.

The JWKS URL is the issuer with `/.well-known/jwks.json` appended.

### Configure the Clerk webhook

After the API has a public HTTPS URL, create a Clerk webhook:

```text
https://API_DOMAIN/api/v1/webhooks/clerk
```

Subscribe to:

- `user.created`;
- `user.updated`;
- `user.deleted`.

Copy the resulting `whsec_...` signing secret. This webhook keeps the
notification email synchronized with Clerk.

## 3. Configure Bright Data

Create or obtain two Web Scraper API dataset IDs:

- an Amazon product dataset;
- an eBay product/listing dataset that returns fixed-price listings.

Each dataset must accept this input shape:

```json
[
  {
    "url": "https://store.example/product"
  }
]
```

The normalizer accepts common output fields including `price`,
`current_price`, `currency`, `shipping_price`, `title`, `image_url`, `asin`,
`item_id`, and the source product URL. Validate each dataset with one manual
collection before enabling the scheduler.

Create a Bright Data API token and record both dataset IDs. Generate a long,
random webhook secret. PriceTracker supplies the callback URL and authorization
header whenever it triggers a snapshot; the worker and API must use the same
webhook secret.

The callback must be:

```text
https://API_DOMAIN/api/v1/webhooks/bright-data
```

## 4. Configure Resend

1. Add and verify a sending domain.
2. Create a restricted sending API key.
3. Choose a sender on the verified domain, for example:

```text
PriceTracker <alerts@your-domain.example>
```

## 5. Run locally with real services

Local real mode still uses local PostgreSQL and Redis, but authentication,
product extraction, and email are real.

### Expose the local API

Clerk and Bright Data cannot call `localhost`. Expose port 8000 with an HTTPS
tunnel, for example:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Keep the tunnel running and record its public HTTPS origin:

```text
https://random-name.trycloudflare.com
```

### Fill the root `.env`

Copy `.env.example` to `.env` if necessary, then set:

```dotenv
# Local runtime with real external services
PRICETRACKER_ENVIRONMENT=development
PRICETRACKER_SERVICE_ROLE=all
PRICETRACKER_DEBUG=false
NEXT_PUBLIC_DEMO_MODE=false

# Local URLs
API_BASE_URL=http://api:8000
PRICETRACKER_FRONTEND_BASE_URL=http://localhost:3000
PRICETRACKER_ALLOWED_ORIGINS=["http://localhost:3000"]

# Clerk frontend
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_REPLACE_ME
CLERK_SECRET_KEY=sk_test_REPLACE_ME
CLERK_JWT_TEMPLATE_NAME=pricetracker-api

# Clerk API verification
PRICETRACKER_FAKE_AUTH_ENABLED=false
PRICETRACKER_CLERK_ISSUER=https://REPLACE_ME.clerk.accounts.dev
PRICETRACKER_CLERK_AUDIENCE=pricetracker-api
PRICETRACKER_CLERK_AUTHORIZED_PARTIES=["http://localhost:3000"]
PRICETRACKER_CLERK_JWKS_URL=https://REPLACE_ME.clerk.accounts.dev/.well-known/jwks.json
PRICETRACKER_CLERK_WEBHOOK_SECRET=whsec_REPLACE_ME

# Bright Data
PRICETRACKER_FAKE_PROVIDER_ENABLED=false
PRICETRACKER_BRIGHT_DATA_API_TOKEN=REPLACE_ME
PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID=gd_REPLACE_ME
PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID=gd_REPLACE_ME
PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL=https://TUNNEL_DOMAIN/api/v1/webhooks/bright-data
PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET=REPLACE_WITH_A_LONG_RANDOM_VALUE

# Resend
PRICETRACKER_RESEND_API_KEY=re_REPLACE_ME
PRICETRACKER_EMAIL_FROM="PriceTracker <alerts@YOUR_VERIFIED_DOMAIN>"
```

Keep the existing local PostgreSQL, Redis, limits, and port values from
`.env.example`. In Compose, the web server's internal API URL is
`http://api:8000`; do not replace it with `localhost`.

Configure the Clerk webhook with the tunnel URL from the previous step:

```text
https://TUNNEL_DOMAIN/api/v1/webhooks/clerk
```

### Validate, rebuild, and start

Public Next.js environment variables are embedded at build time, so rebuild
after changing Clerk or demo-mode values:

```powershell
python scripts/check_live_env.py
docker compose --env-file .env -f infra/compose.yaml down
docker compose --env-file .env -f infra/compose.yaml up -d --build
docker compose --env-file .env -f infra/compose.yaml ps
```

Or with Make:

```powershell
make live-up
```

Wait until `postgres`, `redis`, `api`, `worker`, `scheduler`, and `web` are
healthy.

Open:

- app: <http://localhost:3000>;
- API readiness: <http://localhost:8000/readyz>.

Sign up through Clerk, add one supported product, and confirm:

1. the watch is accepted;
2. the worker creates a Bright Data snapshot;
3. Bright Data calls the public tunnel;
4. the product receives a price observation;
5. an in-app and email alert is created when the target is reached.

Useful diagnostics:

```powershell
docker compose --env-file .env -f infra/compose.yaml logs api
docker compose --env-file .env -f infra/compose.yaml logs worker
docker compose --env-file .env -f infra/compose.yaml logs scheduler
```

## 6. Deploy the backend to Render

### Push a reviewed revision

Commit the repository to a private Git provider repository. Do not commit
`.env` or credentials.

### Create the Blueprint

In Render, create a Blueprint from `infra/render.yaml`. It creates:

- PostgreSQL;
- Redis-compatible key-value storage;
- the FastAPI web service;
- one Celery worker;
- one Celery scheduler.

Use exactly one scheduler instance.

### Fill API variables

For `pricetracker-api`, fill every variable marked for manual synchronization:

```text
PRICETRACKER_FRONTEND_BASE_URL=https://APP_DOMAIN
PRICETRACKER_ALLOWED_ORIGINS=["https://APP_DOMAIN"]
PRICETRACKER_CLERK_ISSUER=https://YOUR_INSTANCE.clerk.accounts.dev
PRICETRACKER_CLERK_AUTHORIZED_PARTIES=["https://APP_DOMAIN"]
PRICETRACKER_CLERK_WEBHOOK_SECRET=whsec_...
PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET=THE_SHARED_RANDOM_SECRET
```

`PRICETRACKER_CLERK_AUDIENCE` is already set to `pricetracker-api`.

### Fill worker variables

For `pricetracker-worker`, set:

```text
PRICETRACKER_BRIGHT_DATA_API_TOKEN=...
PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID=...
PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID=...
PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL=https://API_DOMAIN/api/v1/webhooks/bright-data
PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET=THE_SAME_SHARED_RANDOM_SECRET
PRICETRACKER_RESEND_API_KEY=re_...
PRICETRACKER_EMAIL_FROM=PriceTracker <alerts@YOUR_VERIFIED_DOMAIN>
```

Optional Sentry and OpenTelemetry values can remain blank initially.

The image automatically converts Render's `postgres://` or `postgresql://`
connection URL to SQLAlchemy's `postgresql+asyncpg://` driver URL.

### Verify the backend

After the pre-deploy migration and services complete:

```text
https://API_DOMAIN/healthz
https://API_DOMAIN/readyz
```

Both should return status `ok`. Worker and scheduler must show healthy in
Render before enabling user traffic.

## 7. Deploy the frontend to Vercel

1. Import the repository into Vercel.
2. Keep the Vercel project root at the repository root.
3. Use Node.js 22 and pnpm.
4. Add these Production environment variables:

```text
API_BASE_URL=https://API_DOMAIN
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_JWT_TEMPLATE_NAME=pricetracker-api
```

5. Deploy.
6. Add the final Vercel/custom domain to:
   - Clerk's allowed origins and redirect configuration;
   - `PRICETRACKER_FRONTEND_BASE_URL`;
   - `PRICETRACKER_ALLOWED_ORIGINS`;
   - `PRICETRACKER_CLERK_AUTHORIZED_PARTIES`.
7. Redeploy the API after changing its environment.

Preview deployments should use a separate Clerk instance and should normally
keep fake provider and non-delivery email modes enabled to prevent accidental
spend.

## 8. Configure production webhooks

Update provider callbacks after the production API domain is final:

- Clerk: `https://API_DOMAIN/api/v1/webhooks/clerk`;
- Bright Data:
  `https://API_DOMAIN/api/v1/webhooks/bright-data`.

The Bright Data URL is configured through
`PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL`; the application attaches the shared
Bearer secret to triggered snapshots.

## 9. Final launch checks

Before inviting users:

- all CI checks pass;
- `/readyz` reports healthy;
- API, worker, and exactly one scheduler are running;
- fake auth, fake provider, and frontend demo mode are disabled;
- a real Clerk user can sign in;
- the API accepts the `pricetracker-api` JWT;
- one Amazon product produces a real observation;
- one fixed-price eBay listing produces a real observation;
- auction-format eBay listings are rejected;
- a target crossing creates one in-app alert and one Resend email;
- duplicate webhook delivery does not duplicate the alert;
- Bright Data budget and quota alerts are enabled;
- PostgreSQL backups and a restore procedure are enabled;
- application secrets are stored only in provider secret stores.

After launch, monitor provider spend, queue age, stale prices, webhook failures,
email failures, database capacity, and scheduler uniqueness.
