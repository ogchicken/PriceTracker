# Obtaining every secret in `.env`

This guide explains where each value in `.env` comes from and walks through the
provider dashboards click by click. Follow it once before the first deploy
(see [deployment.md](deployment.md)); afterwards you only return here when
rotating a credential.

Rules that apply to everything below:

- Never commit `.env` or paste secrets into issues, chats, or logs.
- Keep **separate credentials for development and production** — a Clerk
  development instance and test keys locally, the production instance and live
  keys on the VPS.
- On the VPS, `.env` should be readable only by the deploy user
  (`chmod 600 .env`).

## Overview: every variable and where it comes from

| Variable | Source | Used by |
| --- | --- | --- |
| `COMPOSE_PROFILES` | you choose: `dev` locally, `prod` on the VPS | docker compose |
| `DOMAIN` | your DNS provider (the domain pointing at the VPS) | caddy |
| `ACME_EMAIL` | your email address (Let's Encrypt expiry notices) | caddy |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | [Clerk](#clerk) → API keys (`pk_...`) | web (baked at build) |
| `CLERK_SECRET_KEY` | [Clerk](#clerk) → API keys (`sk_...`) | web (server) |
| `CLERK_JWT_TEMPLATE_NAME` | [Clerk](#clerk) → JWT template you create (`pricetracker-api`) | web (server) |
| `API_BASE_URL` | fixed: `http://api:8000` in Compose, `http://localhost:8000` host dev | web (server) |
| `PRICETRACKER_ENVIRONMENT` | you choose: `development` / `production` | api, worker, scheduler |
| `PRICETRACKER_SERVICE_ROLE` | fixed: `all` (single-VPS stack) | api, worker, scheduler |
| `PRICETRACKER_DEBUG`, `PRICETRACKER_LOG_LEVEL` | you choose | api, worker, scheduler |
| `PRICETRACKER_ALLOWED_ORIGINS` | derived: `["https://$DOMAIN"]` in production | api |
| `PRICETRACKER_FRONTEND_BASE_URL` | derived: `https://$DOMAIN` in production | api |
| `POSTGRES_DB`, `POSTGRES_USER` | you choose (defaults are fine) | postgres, api services |
| `POSTGRES_PASSWORD` | [self-generated](#self-generated) | postgres, api services |
| `PRICETRACKER_DATABASE_URL` | derived from the Postgres values (keep the example line) | host-run dev commands |
| `PRICETRACKER_REDIS_URL` / `..._CELERY_*` | fixed (keep the example lines) | host-run dev commands |
| `PRICETRACKER_CLERK_ISSUER` | [Clerk](#clerk) → Frontend API URL | api |
| `PRICETRACKER_CLERK_AUDIENCE` | fixed: `pricetracker-api` (matches the JWT template) | api |
| `PRICETRACKER_CLERK_AUTHORIZED_PARTIES` | derived: `["https://$DOMAIN"]` in production | api |
| `PRICETRACKER_CLERK_JWKS_URL` | derived: issuer + `/.well-known/jwks.json` | api |
| `PRICETRACKER_CLERK_WEBHOOK_SECRET` | [Clerk](#clerk) → Webhooks endpoint (`whsec_...`) | api |
| `PRICETRACKER_BRIGHT_DATA_API_BASE_URL` | fixed: `https://api.brightdata.com` | worker |
| `PRICETRACKER_BRIGHT_DATA_API_TOKEN` | [Bright Data](#bright-data) → account settings | worker |
| `PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID` | [Bright Data](#bright-data) → Amazon dataset (`gd_...`) | worker |
| `PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID` | [Bright Data](#bright-data) → eBay dataset (`gd_...`) | worker |
| `PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET` | [self-generated](#self-generated) | api + worker (shared) |
| `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL` | derived: `https://$DOMAIN/api/v1/webhooks/bright-data` | worker |
| `PRICETRACKER_RESEND_API_KEY` | [Resend](#resend) → API keys (`re_...`) | worker |
| `PRICETRACKER_EMAIL_FROM` | [Resend](#resend) → address on your verified domain | worker |
| tuning values (`PRICETRACKER_TRACKING_*`, limits) | defaults are sensible | api, worker, scheduler |
| `*_PORT`, `WORKER_CONCURRENCY` | defaults are sensible | docker compose |

Quick split of what you **mint yourself** versus what a **provider issues**:

- Self-generated: `POSTGRES_PASSWORD`, `PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET`.
- Provider-issued: both Clerk keys, the Clerk webhook secret, the Bright Data
  API token and dataset IDs, the Resend API key.
- Everything else is either fixed, chosen by you, or derived from `$DOMAIN`.

## Clerk

Clerk provides sign-in for the web app and the JWTs the API verifies.
Create an account at <https://dashboard.clerk.com>.

### 1. Create the application

1. In the Clerk Dashboard click **Create application**.
2. Name it (e.g. `PriceTracker`) and enable the sign-in options you want
   (email, Google, ...).
3. Every Clerk application has a **Development** instance; you create the
   **Production** instance when you attach your domain (step 5). Use
   development-instance keys locally and production-instance keys on the VPS.

### 2. Copy the API keys

1. Go to **Configure → API keys**.
2. Copy the **Publishable key** → `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   (`pk_test_...` for development, `pk_live_...` for production).
3. Copy the **Secret key** → `CLERK_SECRET_KEY` (`sk_test_...` /
   `sk_live_...`).

### 3. Create the JWT template

The web app mints a short-lived token from this template for every API call;
the API verifies its audience.

1. Go to **Configure → JWT templates → New template → Blank**.
2. Name: `pricetracker-api` (must equal `CLERK_JWT_TEMPLATE_NAME`).
3. Token lifetime: 60 seconds; allowed clock skew: 5 seconds.
4. Claims:

   ```json
   {
     "aud": "pricetracker-api",
     "email": "{{user.primary_email_address}}"
   }
   ```

5. Save. The `aud` value must equal `PRICETRACKER_CLERK_AUDIENCE`.

### 4. Record the issuer and JWKS URL

1. Go to **Configure → API keys** and find the **Frontend API URL**, e.g.
   `https://your-instance.clerk.accounts.dev` (development) or
   `https://clerk.your-domain.com` (production).
2. That URL is `PRICETRACKER_CLERK_ISSUER`.
3. `PRICETRACKER_CLERK_JWKS_URL` is the issuer with
   `/.well-known/jwks.json` appended.
4. `PRICETRACKER_CLERK_AUTHORIZED_PARTIES` is a JSON list of the exact
   browser origins that may present tokens: `["http://localhost:3000"]` in
   development, `["https://app.example.com"]` in production.

### 5. Production instance (VPS deploys)

1. In the Clerk Dashboard switch the instance selector to **Production** and
   follow Clerk's flow to attach your domain (it asks for a few DNS records —
   CNAMEs for `clerk.`, `accounts.`, and email — add them at your DNS
   provider and wait for verification).
2. Re-copy the **production** publishable/secret keys and the production
   Frontend API URL into the VPS `.env`.

### 6. Webhook (after the first deploy)

This keeps user records in sync when accounts change in Clerk. It needs the
live HTTPS domain, so do it after the first deploy:

1. Go to **Configure → Webhooks → Add endpoint**.
2. Endpoint URL: `https://app.example.com/api/v1/webhooks/clerk`.
3. Subscribe to `user.created`, `user.updated`, and `user.deleted` only.
4. Create the endpoint, open it, and reveal the **Signing secret**
   (`whsec_...`) → `PRICETRACKER_CLERK_WEBHOOK_SECRET`.
5. Redeploy so the API picks it up.

## Bright Data

Bright Data performs the actual Amazon/eBay price collections through its Web
Scraper API. **Collections cost money** — set up budget alerts before letting
the scheduler run. Create an account at <https://brightdata.com>.

### 1. API token

1. In the Bright Data control panel open **Account settings** (or your
   profile menu) and find the **API tokens** section.
2. Create (or reveal) an API token → `PRICETRACKER_BRIGHT_DATA_API_TOKEN`.

### 2. Dataset IDs

PriceTracker triggers "collect by URL" snapshots against two Web Scraper API
datasets:

1. Open **Web Scraper API** (also listed as "Web Scrapers" / "Datasets &
   Web Scraper API" in the console) and browse the scraper library.
2. Locate the **Amazon product** scraper and open its API/playground page —
   the dataset ID looks like `gd_xxxxxxxxxxxxxxxxx`. Copy it into
   `PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID`.
3. Do the same for the **eBay product/listing** scraper (it must return
   fixed-price listings) → `PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID`.
4. Each dataset must accept this input shape:

   ```json
   [{ "url": "https://store.example/product" }]
   ```

   The normalizer understands common output fields (`price`, `current_price`,
   `currency`, `shipping_price`, `title`, `image_url`, `asin`, `item_id`, and
   the source URL). Validate each dataset with one manual collection in the
   Bright Data playground before enabling the scheduler.

### 3. Webhook URL and secret

Bright Data delivers results by calling your API back. You do **not**
configure this in their dashboard — PriceTracker supplies the callback URL and
an authorization header every time it triggers a snapshot:

- `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL` =
  `https://app.example.com/api/v1/webhooks/bright-data`
  (must be public HTTPS; for local pipeline testing use an HTTPS tunnel such
  as `cloudflared tunnel --url http://localhost:8000`).
- `PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET` = a long random value you
  generate yourself (see [below](#self-generated)). The API rejects callbacks
  that do not present it.

### 4. Budget alerts

In the Bright Data console, configure spending limits/alerts for your zone or
account so a runaway schedule cannot surprise you.

## Resend

Resend sends the price-alert emails. Create an account at
<https://resend.com>.

### 1. Verify a sending domain

1. Go to **Domains → Add domain** and enter the domain you will send from
   (e.g. `example.com` or `mail.example.com`).
2. Resend shows DNS records (SPF/TXT and DKIM CNAMEs, optionally DMARC). Add
   them at your DNS provider.
3. Wait for the domain to show **Verified**.

### 2. Create the API key

1. Go to **API keys → Create API key**.
2. Scope it to **Sending access** only, restricted to your domain.
3. Copy the key (`re_...`) → `PRICETRACKER_RESEND_API_KEY`. It is shown only
   once.

### 3. Choose the sender

Set `PRICETRACKER_EMAIL_FROM` to an address on the verified domain, in
display-name form:

```text
PriceTracker <alerts@example.com>
```

The API refuses to start in production while the sender still uses the
`example.test` placeholder.

Development note: a **blank** `PRICETRACKER_RESEND_API_KEY` makes the backend
log emails instead of sending them — no Resend account is needed until you
want real delivery.

## Self-generated

Two secrets are minted by you, not issued by a provider. Generate them with
OpenSSL (or any password manager's generator):

```bash
# PostgreSQL password (avoid characters that need URL-escaping)
openssl rand -hex 24

# Bright Data webhook shared secret
openssl rand -hex 32
```

- `POSTGRES_PASSWORD` — used by the postgres container and every API-role
  service. If you change it after the first boot, you must also change it
  inside PostgreSQL (`ALTER USER pricetracker PASSWORD '...'`) or reset the
  `postgres-data` volume.
- `PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET` — shared between the worker
  (which attaches it to snapshot triggers) and the API (which requires it on
  incoming Bright Data callbacks). One value, used by both; at least 24
  characters (the validator warns below that).

## Rotating secrets

1. Generate/issue the new value at the provider (or with OpenSSL).
2. Update `.env` on the VPS.
3. Run `./scripts/deploy.sh` — it rebuilds (picking up `NEXT_PUBLIC_*`
   changes) and restarts every service with the new environment.
4. Revoke the old credential at the provider once the deploy is healthy.

If a secret may have leaked, rotate immediately and follow
[SECURITY.md](../SECURITY.md).
