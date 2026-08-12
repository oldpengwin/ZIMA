# Security Policy

We take the security and privacy of ZIMA's builders seriously. Thank you for
helping keep the platform safe.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, report privately via one of:

- GitHub's **[Private vulnerability reporting](https://github.com/oldpengwin/ZIMA/security/advisories/new)**
  (Security tab → *Report a vulnerability*), or
- Email the maintainers (see the repository owner's profile).

Please include:

- A description of the issue and its impact.
- Steps to reproduce (a proof of concept if possible).
- Affected component (backend API, Discord bot, frontend, infra).

### What to expect

- We aim to acknowledge reports within **3 business days**.
- We'll keep you updated as we investigate and fix.
- We're happy to credit you in the advisory once a fix ships, unless you'd
  prefer to remain anonymous.

## Scope

In scope: the API (`src/api`, `src/core`, `src/services`), the Discord bot
(`src/features`, `src/handlers`, `src/roles`), the database layer, and
deployment configuration.

Out of scope: findings that require a compromised host or physical access;
issues in third-party dependencies already tracked by Dependabot (report those
upstream); social-engineering or spam.

## Handling of user data

ZIMA is privacy-first by design:

- Personal data is used only for the feature at hand.
- Public endpoints never expose a user's `discord_id`.
- Account deletion is immediate and produces an auditable report of exactly
  what was removed, orphaned, or anonymized.

If you find a case where personal data leaks or deletion is incomplete, please
report it with the same private process above — we treat privacy issues as
security issues.
