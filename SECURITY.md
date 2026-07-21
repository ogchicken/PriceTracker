# Security Policy

## Supported versions

Until a stable release exists, only the latest commit on `main` receives
security fixes. After versioned releases begin, this table must be updated with
the supported release lines.

## Reporting a vulnerability

Do not open a public issue or include exploit details in logs, screenshots, or
pull requests.

Use GitHub's **Security** tab to submit a private vulnerability report. If
private vulnerability reporting is not enabled, contact the repository owner
privately and ask for a secure reporting channel. Replace this paragraph with a
monitored security address before public launch.

Include, when possible:

- the affected component and revision;
- reproduction steps or a minimal proof of concept;
- expected and observed impact;
- whether credentials or real user data were involved;
- suggested mitigations.

The maintainers should acknowledge a complete report within three business
days, provide an initial severity assessment within seven business days, and
coordinate disclosure after a fix is available. These are response targets,
not a bug-bounty promise.

## Security-sensitive areas

Reports involving the following are especially important:

- Clerk JWT verification, authorization, or account isolation;
- Clerk and Bright Data webhook signature verification or replay protection;
- cross-user access to products, watches, price history, or alerts;
- server-side request forgery through submitted product URLs;
- exposed database, Redis, Resend, Clerk, Bright Data, or deployment secrets;
- injection into scraping, email, task, or database workflows;
- bypasses of price-check rate limits or paid-provider cost controls.

## Secret exposure

If a secret may have been committed or disclosed, revoke and rotate it
immediately. Removing it from the latest commit does not remove it from Git
history. Review provider audit logs, invalidate active sessions if relevant,
and document the incident without copying the secret.

Production credentials must live in the deployment platform's encrypted secret
store. Only Clerk's publishable key may use a `NEXT_PUBLIC_` prefix.

