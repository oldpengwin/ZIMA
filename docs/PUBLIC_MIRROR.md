# ZIMA public-mirror system — design & operator guide

**Status:** internal (this file is on `.public-deny`, so it never ships to the
mirror). Approved design, 2026-08-12.

## Goal

Keep the whole codebase **private** (the team's single source of truth), while
exposing a **curated, browsable public subset** on GitHub for a technical
audience — "here's how ZIMA is built" — without ever leaking secrets or the
core IP (the matching algorithm and its weights).

GitHub has no per-file visibility: a repo is entirely private or entirely
public, history included. So we don't toggle this repo. We **generate** a
separate public repo from an allowlist.

## Architecture

```
  oldpengwin/ZIMA  (PRIVATE, this repo)              oldpengwin/zima-showcase (PUBLIC)
  ─────────────────────────────────────             ────────────────────────────────
  all source, team sees everything                   only allowlisted files
        │                                            clean history (public files only)
        │  push to main                                        ▲
        ▼                                                      │
  .github/workflows/publish-mirror.yml ──── builds allowlisted tree, secret-scans,
                                             pushes a fresh clean tree ─────────────┘
```

**Deny-by-default** is the whole safety model: a file is private unless it is
explicitly allowlisted. Forgetting a file cannot leak it; only adding a line can.

## The three control files (repo root)

| File | Role |
|---|---|
| `.public-allow` | Globs that **are** published. Your "public tier" tag. |
| `.public-deny` | Hard fuse — **always wins** over allow (secrets, IP, internal docs). |
| `.public-exclude` | Files a human reviewed and deliberately kept private (so `--check` stays green and the classifier stops re-asking). Normally written by the tool, not by hand. |

Precedence for any file: **deny → public → private(exclude) → undecided.**

Syntax is gitignore-style, root-anchored: `demo/**`, `README.md`, `**/*.md`,
`dir/` (= everything under dir).

## The classifier — `scripts/classify_public.py`

Stdlib-only, no dependencies. Commands:

```bash
python scripts/classify_public.py                     # interactive: asks p/k/s for each UNDECIDED file
python scripts/classify_public.py --keep-rest-private  # mark all undecided files private in one shot
python scripts/classify_public.py --summary            # counts: public / private / blocked / undecided
python scripts/classify_public.py --check              # CI gate (exit 1 on undecided files or allow∩deny)
python scripts/classify_public.py --list               # resolved public paths (used by the workflow)
```

The interactive mode is the "**ask whether each file is open or closed**"
step you wanted. `--check` in CI makes it *enforced*: a newly-added, still-
undecided file fails the build, so no file reaches `main` without a decision.

## The sync — `.github/workflows/publish-mirror.yml`

Runs in this private repo on push to `main` (and manual dispatch):

1. `--check` gate: fail if anything is undecided or on both allow+deny.
2. Build `_public_out/` = allowlist **minus** denylist, only.
3. **gitleaks** secret-scan of `_public_out/` — the last fuse before it leaves.
4. Clone the mirror, replace its tracked contents wholesale with `_public_out/`,
   commit, push to `main`.

Because the mirror's tree is rebuilt from the allowlist every run, its history
can only ever contain public files — no private path, content, or commit
message can bleed across, past or present. Removing a file from `.public-allow`
also removes it from the mirror on the next run.

## One-time setup

1. **Create the public repo** (empty, no README) — already done for
   `oldpengwin/zima-showcase`:
   ```bash
   gh repo create oldpengwin/zima-showcase --public --description "Public mirror of ZIMA"
   ```
   If you name it differently, update `MIRROR_REPO` in the workflow's `env:` block.

2. **Set up a write-scoped deploy key** (a scoped SSH key for the mirror repo
   only — not a personal PAT). From the repo root:
   ```bash
   ssh-keygen -t ed25519 -N "" -C "zima-mirror-sync" -f mirror_key
   gh repo deploy-key add mirror_key.pub --repo oldpengwin/zima-showcase --title zima-mirror-sync --allow-write
   gh secret set MIRROR_DEPLOY_KEY --repo oldpengwin/ZIMA < mirror_key
   rm -f mirror_key mirror_key.pub          # delete the local copies once the secret is set
   ```
   The private half lives only as the `MIRROR_DEPLOY_KEY` secret; the public
   half is a write deploy key on the mirror. Neither is your personal token.

4. **Classify the existing tree once** (locally, from the private repo root):
   ```bash
   python scripts/classify_public.py --summary          # see what's undecided
   python scripts/classify_public.py                     # optionally mark a few public
   python scripts/classify_public.py --keep-rest-private # sweep the rest to private
   python scripts/classify_public.py --check             # should now pass
   ```
   Commit the updated control files. The next push to `main` publishes the mirror.

## Day-to-day

- Add a file → next `--check` will flag it undecided until you classify it.
- Want to show off a specific file publicly? Add one line to `.public-allow`
  (unless `.public-deny` blocks it). Review that line like any security change.
- Want to un-publish something? Remove its allow line; the next sync drops it
  from the mirror.

## Initial classification (this design's decision)

**Public:** `demo/**`, `README.md`, `Archetypes.md`, `LICENSE`.
**Blocked (never public):** secrets/env, `src/core/neurotype_matcher.py`,
`src/services/matching_service.py` (core IP), and the internal docs
(`README.internal.md`, `IMPLEMENTATION_PLAN.md`, `REPOSITORY_SUMMARY.md`,
this file).
**Everything else:** private by default.

## Guarantees & limits

- **Guarantees:** deny-by-default; a category fuse that overrides careless
  allow lines; a secret scan on the exact bytes being published; a mirror
  history that structurally cannot contain private files; a CI gate that
  forces a human decision on every new file.
- **Limits:** the guarantees protect the *mirror*. They do nothing about the
  private repo's own history (that's the separate secret-scrub already done).
  And `LICENSE` is a conservative "source-available, all rights reserved"
  default — change it consciously if you want OSS terms (see the note in the
  file).
