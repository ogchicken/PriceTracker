# Privacy Notice — Draft

> **Draft for legal review.** This template is not legal advice and is not
> ready for publication. Replace every bracketed placeholder, verify actual
> product behavior, vendors, retention periods, and legal bases, and obtain
> qualified counsel before launch.

**Proposed effective date:** [DATE]  
**Operator:** [LEGAL ENTITY AND ADDRESS]  
**Privacy contact:** [PRIVACY EMAIL]

This notice describes how [OPERATOR] would process information when people use
PriceTracker.

## Information collected

Depending on the implemented features, PriceTracker may process:

- account identifiers, name, email address, authentication events, and profile
  details supplied through Clerk;
- product URLs, retailer/product identifiers, watch settings, target prices,
  alert preferences, and interaction history;
- observed prices, availability, timestamps, and provider provenance;
- IP address, user agent, request metadata, cookie/session identifiers, logs,
  crash reports, and coarse device information;
- support messages and privacy/security requests.

Do not state that payment information is collected unless billing is actually
implemented. Document any analytics, cookies, or marketing tools before using
them.

## Why information is used

Subject to applicable law and the final legal basis analysis, information may
be used to:

- provide accounts, watches, price history, and requested alerts;
- authenticate users and prevent fraud, abuse, and unauthorized access;
- collect current retailer data and troubleshoot failed checks;
- maintain, measure, secure, and improve the service;
- communicate service, support, security, and policy updates;
- comply with law and enforce terms.

The final notice must identify applicable legal bases, including contract,
legitimate interests, consent, or legal obligation, for each relevant
jurisdiction.

## Service providers and disclosures

PriceTracker is expected to use:

- Clerk for identity and authentication;
- Bright Data for retail-data collection;
- Resend for transactional email;
- cloud hosting, managed PostgreSQL/Redis, logging, error-reporting, and
  observability providers selected by [OPERATOR].

These providers process information under their own terms and the agreements
with [OPERATOR]. Complete this list with vendor names, purposes, locations,
subprocessor links, and any analytics or support systems before publication.

Information may also be disclosed when required by law, to protect users and
the service, in a corporate transaction, or with a user's direction or
consent. PriceTracker must not claim to sell or share information for targeted
advertising unless that statement has been verified under applicable laws.

## Retailer data and submitted URLs

Product URLs and identifiers may be sent to Bright Data or retailers to
retrieve public product information. A user's email address or account profile
should not be sent to retailers or scraping providers unless strictly required
and disclosed.

## Retention

Define and enforce concrete retention schedules before launch. Proposed
categories requiring decisions include:

- account records while an account is active plus [PERIOD];
- watches and price history for [PERIOD] after deletion/account closure;
- webhook/provider job records for [PERIOD];
- alert-delivery records for [PERIOD];
- security and application logs for [PERIOD];
- backups on a rolling [PERIOD] schedule.

Deletion from active systems may not immediately remove data from encrypted
backups; the final notice must state when backups expire. Retain information
longer only when required for security, disputes, or law, and document the
reason.

## Choices and rights

Depending on location, a person may have rights to access, correct, delete, or
export information; object to or restrict processing; withdraw consent; and
appeal a decision. Provide an authenticated in-product request path and a
contact method at [PRIVACY EMAIL]. Verify identity without collecting
excessive additional data and respond within applicable deadlines.

Document cookie choices and opt-outs if nonessential cookies or analytics are
introduced. Transactional alert emails should include an appropriate way to
disable the watch or its notifications.

## International transfers

PriceTracker and its providers may process information in countries other than
the user's country. Before publication, identify hosting/processing locations
and the transfer safeguards used where required, such as adequacy decisions or
standard contractual clauses.

## Security

PriceTracker uses administrative, technical, and organizational safeguards
intended to protect information, but no service is completely secure. The
final description must reflect controls that actually exist and must not
promise absolute security.

Security concerns should follow [SECURITY.md](../SECURITY.md). Privacy requests
should use [PRIVACY EMAIL].

## Children

PriceTracker is not intended for children under [MINIMUM AGE]. The minimum age
and any parental-consent process must be selected for the launch
jurisdictions. If [OPERATOR] learns that information was collected contrary to
that policy, it will take appropriate deletion steps.

## Changes

[OPERATOR] may update this notice as the service or law changes. The published
version should show its effective date and describe how material changes are
communicated.

## Contact

[LEGAL ENTITY]  
[POSTAL ADDRESS]  
[PRIVACY EMAIL]  
[DATA PROTECTION OFFICER OR EU/UK REPRESENTATIVE, IF APPLICABLE]

