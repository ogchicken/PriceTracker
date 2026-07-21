# Deployment: single VPS with Docker Compose

This guide takes you from a fresh VPS to a running, HTTPS-secured PriceTracker
deployment, and covers redeploys, backups, and rollback. Obtaining the secrets
referenced here is covered step by step in [secrets.md](secrets.md).

## 1. Topology

Everything runs on one VPS in one Docker Compose project:

```text
                         Internet
                            |
                    443/80 (only public ports)
                            v
                    +---------------+
                    | caddy         |  TLS via Let's Encrypt for $DOMAIN
                    +---------------+
                     |            |
        (default)    v            v   /api/*, /healthz, /readyz
              +-----------+  +-----------+
              | web :3000 |  | api :8000 |
              +-----------+  +-----------+
                     |         |     |
                     |         v     v
                     |  +----------+ +---------+
                     +->| postgres | |  redis  |
                        +----------+ +---------+
                              ^          ^
                        +-----------+ +-----------+
                        |  worker   | | scheduler |
                        +-----------+ +-----------+
```

- Caddy is the only service listening on public interfaces (80/443). It
  requests and renews the TLS certificate automatically.
- Requests to `/api/*`, `/healthz`, and `/readyz` go to FastAPI; everything
  else goes to Next.js. Clerk and Bright Data webhooks arrive at
  `https://$DOMAIN/api/v1/webhooks/...`.
- PostgreSQL, Redis, the API, and the web server publish ports only on the
  VPS loopback (`127.0.0.1`) for debugging; they are not reachable from the
  internet.
- `/metrics` (Prometheus) is intentionally not routed publicly; read it on the
  VPS via `curl http://127.0.0.1:8000/metrics`.
- Migrations run through the one-shot `migrate` service, invoked by the deploy
  script before the stack restarts.
- One `.env` file at the repository root configures everything.

## 2. Prerequisites

- A **domain** (or subdomain) you control, e.g. `app.example.com`.
- A **VPS** running Ubuntu 24.04 LTS with at least 2 GB RAM (4 GB is
  comfortable; the web image build alone wants ~1 GB free) and 20+ GB disk.
  Any provider works (Hetzner, DigitalOcean, Vultr, OVH, ...).
- SSH access to the VPS as root or a sudo user.
- Accounts and credentials for **Clerk**, **Bright Data**, and **Resend** —
  collect them with [secrets.md](secrets.md) before the first deploy.

## 3. Point DNS at the VPS

At your DNS provider, create records for your chosen domain:

| Type | Name | Value |
| --- | --- | --- |
| A | `app` (or `@`) | the VPS IPv4 address |
| AAAA | `app` (or `@`) | the VPS IPv6 address (if it has one) |

Use a modest TTL (300–3600 s). Verify propagation before the first deploy —
Let's Encrypt issuance fails until the domain resolves to the VPS:

```bash
dig +short app.example.com
```

## 4. Prepare the server

SSH in as root (or your provider's default sudo user):

```bash
ssh root@YOUR_VPS_IP
```

Create a deploy user with sudo and key-based SSH:

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
rsync -a ~/.ssh/ /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
```

Update packages and enable automatic security updates:

```bash
apt-get update && apt-get -y upgrade
apt-get -y install unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades
```

Configure the firewall — SSH plus HTTP/HTTPS only:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

Optionally harden SSH (`/etc/ssh/sshd_config`): set
`PasswordAuthentication no` and `PermitRootLogin no`, then
`systemctl restart ssh`. Make sure key-based login as `deploy` works first.

From here on, work as the deploy user: `ssh deploy@YOUR_VPS_IP`.

## 5. Install Docker Engine and the Compose plugin

Use Docker's official repository (Ubuntu's packaged docker is outdated):

```bash
sudo apt-get update
sudo apt-get -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Let the deploy user run docker without sudo, then re-login:

```bash
sudo usermod -aG docker $USER
exit
```

```bash
ssh deploy@YOUR_VPS_IP
docker version && docker compose version
```

## 6. Clone the repository

```bash
sudo mkdir -p /opt/pricetracker
sudo chown $USER:$USER /opt/pricetracker
git clone https://github.com/YOUR_GITHUB_USER/PriceTracker.git /opt/pricetracker
cd /opt/pricetracker
```

For a private repository, use a fine-grained access token or a read-only
deploy key.

## 7. Create the production `.env`

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Work through the file top to bottom — every secret's origin is documented in
[secrets.md](secrets.md). The production values that differ from the local
defaults:

```dotenv
# Deployment
COMPOSE_PROFILES=prod
DOMAIN=app.example.com
ACME_EMAIL=you@example.com

# API runtime
PRICETRACKER_ENVIRONMENT=production
PRICETRACKER_DEBUG=false
PRICETRACKER_ALLOWED_ORIGINS=["https://app.example.com"]
PRICETRACKER_FRONTEND_BASE_URL=https://app.example.com

# Web — production Clerk instance keys (pk_live_/sk_live_)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
API_BASE_URL=http://api:8000

# PostgreSQL — generated password (openssl rand -hex 24)
POSTGRES_PASSWORD=GENERATED_VALUE

# Clerk verification
PRICETRACKER_CLERK_ISSUER=https://clerk.app.example.com        # or ...clerk.accounts.dev
PRICETRACKER_CLERK_AUTHORIZED_PARTIES=["https://app.example.com"]
PRICETRACKER_CLERK_JWKS_URL=https://YOUR_ISSUER/.well-known/jwks.json
PRICETRACKER_CLERK_WEBHOOK_SECRET=whsec_pending                # added after step 9

# Bright Data
PRICETRACKER_BRIGHT_DATA_API_TOKEN=...
PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID=gd_...
PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID=gd_...
PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET=GENERATED_VALUE        # openssl rand -hex 32
PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL=https://app.example.com/api/v1/webhooks/bright-data

# Resend
PRICETRACKER_RESEND_API_KEY=re_...
PRICETRACKER_EMAIL_FROM="PriceTracker <alerts@example.com>"
```

Notes:

- `API_BASE_URL` stays `http://api:8000` — it is the internal address the web
  container uses to reach the API on the Compose network.
- Keep the `PRICETRACKER_DATABASE_URL`/`PRICETRACKER_REDIS_URL` lines from the
  example as-is; Compose overrides the hosts per service, and the API refuses
  `localhost` data URLs in production anyway.
- The Clerk webhook secret does not exist until step 9; leave the placeholder,
  finish the first deploy, then fill it in and redeploy.

Validate before deploying (the deploy script also runs this):

```bash
python3 scripts/check_live_env.py --env-file .env
```

## 8. First deploy

```bash
cd /opt/pricetracker
./scripts/deploy.sh
```

The script, in order: pulls the latest commit (`git pull --ff-only`),
validates `.env`, builds all images, applies database migrations via the
one-shot `migrate` service, starts the stack, waits for the API to report
ready on the loopback port, and finally checks `https://$DOMAIN/healthz`.

The first run builds every image and takes several minutes. Watch certificate
issuance if the final public check warns:

```bash
docker compose --env-file .env -f infra/compose.yaml logs -f caddy
```

Successful issuance logs `certificate obtained successfully`. Then verify:

```bash
curl https://app.example.com/healthz    # {"status":"ok"}
curl https://app.example.com/readyz     # {"status":"ok", ...}
docker compose --env-file .env -f infra/compose.yaml ps   # all services healthy
```

> Never run a bare `docker compose up -d` on a fresh clone — migrations only
> run through `scripts/deploy.sh` (or explicitly via
> `docker compose --env-file .env -f infra/compose.yaml run --rm migrate`).

> **Running Compose by hand:** the `docker compose` commands throughout this
> guide pass `--env-file .env`, but profiled services (`caddy` under the `prod`
> profile) only appear when `COMPOSE_PROFILES` is active in your shell.
> `scripts/deploy.sh` exports it for you; for manual commands, export it to
> match `.env` first — `export COMPOSE_PROFILES=prod` — otherwise
> `... ps` / `... logs caddy` won't see the proxy.

## 9. Wire the webhooks (needs the live HTTPS domain)

Now that `https://$DOMAIN` exists, connect the providers (dashboard
walkthroughs in [secrets.md](secrets.md)):

1. **Clerk webhook** — in the Clerk Dashboard add an endpoint
   `https://app.example.com/api/v1/webhooks/clerk` subscribed to
   `user.created`, `user.updated`, `user.deleted`. Copy the generated signing
   secret (`whsec_...`) into `PRICETRACKER_CLERK_WEBHOOK_SECRET` in `.env`,
   then redeploy: `./scripts/deploy.sh`.
2. **Bright Data** — nothing to configure in their dashboard for callbacks:
   the application passes `PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL` and the
   shared secret with every triggered snapshot. Just confirm the URL in
   `.env` is `https://app.example.com/api/v1/webhooks/bright-data`.

## 10. Launch verification

Walk the product end to end:

1. Open `https://app.example.com`, sign up through Clerk, and land on the
   dashboard.
2. Add one supported Amazon or eBay (fixed-price) product with a target price.
3. Watch the worker trigger a collection:

   ```bash
   docker compose --env-file .env -f infra/compose.yaml logs -f worker
   ```

4. Confirm Bright Data calls back (api logs show the webhook) and the item
   shows a real price and title.
5. Set a target above the current price and confirm one in-app notification
   and one Resend email arrive when it is reached.
6. Confirm Bright Data budget alerts are configured — every collection costs
   money.

## 11. Redeploying during development

Push to `main`, then:

```bash
ssh deploy@YOUR_VPS_IP '/opt/pricetracker/scripts/deploy.sh'
```

or from your machine with Make:

```bash
make deploy VPS_HOST=deploy@YOUR_VPS_IP
```

The script is idempotent — run it as often as you like. Notes:

- `NEXT_PUBLIC_*` values are baked into the web image at build time. The
  deploy script always rebuilds, so changing the publishable key just needs a
  normal redeploy.
- Migrations run before the new containers start; write them
  expand-then-contract so the previous code keeps working during the brief
  overlap.
- Old images are pruned automatically at the end of each deploy.

## 12. Backups

Dump PostgreSQL from the running container:

```bash
docker compose --env-file .env -f infra/compose.yaml exec -T postgres \
  pg_dump -U pricetracker -d pricetracker -F c > /opt/backups/pricetracker-$(date +%F).dump
```

Automate it with cron (`crontab -e`):

```cron
15 3 * * * mkdir -p /opt/backups && docker compose --env-file /opt/pricetracker/.env -f /opt/pricetracker/infra/compose.yaml exec -T postgres pg_dump -U pricetracker -d pricetracker -F c > /opt/backups/pricetracker-$(date +\%F).dump 2>> /opt/backups/backup.log
```

Copy dumps off the VPS (object storage, `rclone`, or your provider's snapshot
feature) — a backup on the same disk is not a backup. Test restores
periodically:

```bash
docker compose --env-file .env -f infra/compose.yaml exec -T postgres \
  pg_restore -U pricetracker -d pricetracker --clean --if-exists < /opt/backups/pricetracker-2026-07-21.dump
```

Redis holds only queue/coordination state and needs no backup; the
`caddy-data` volume holds certificates and re-issues automatically if lost.

## 13. Rollback

To roll back to a known-good commit:

```bash
cd /opt/pricetracker
git log --oneline -10          # find the good commit
git checkout GOOD_COMMIT_SHA
docker compose --env-file .env -f infra/compose.yaml build
docker compose --env-file .env -f infra/compose.yaml up -d --remove-orphans
```

(`deploy.sh` is not used here because `git pull --ff-only` would move you
forward again. Return to normal deploys with `git checkout main`.)

Caveat: rolling back code does not roll back applied migrations. If the bad
release included a destructive migration, restore the database from the latest
backup instead of downgrading in place.

## 14. Troubleshooting

- **Certificate issuance fails / public health check warns:** confirm DNS
  resolves to the VPS (`dig +short $DOMAIN`), ports 80/443 are open
  (`sudo ufw status`), and nothing else binds them (`sudo ss -tlnp | grep -E ':80|:443'`).
  Then watch `... logs -f caddy`. Let's Encrypt rate-limits repeated failures —
  fix DNS before retrying repeatedly.
- **502 from Caddy:** the target container is unhealthy. Check
  `... ps` and the failing service's logs (`... logs api`, `... logs web`).
- **API stuck unhealthy after deploy:** usually production config validation —
  `... logs api` prints the exact missing/invalid setting (the same rules
  `check_live_env.py` enforces).
- **Migration step fails:** the stack keeps running the previous version.
  Inspect the `migrate` output printed by the deploy script, fix the
  migration, redeploy.
- **Port conflicts on the VPS:** another service owns 80/443 (often a stray
  nginx/apache). Stop and disable it, or change the published ports.
- **Web image build runs out of memory:** add swap
  (`sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`)
  or build on a bigger box.
- **Webhook signature failures:** confirm the secrets in `.env` match the
  provider dashboards and redeploy; Caddy passes bodies through unmodified.
