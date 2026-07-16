# Zima — Demo Build Deployment Guide

A plain-language, step-by-step walkthrough to get the Zima demo bot **live in your Discord server**. No coding required — you'll copy IDs into one file and run a few commands.

Written for the `ZIMA/` build in this folder. Follow it top to bottom; each part builds on the last. Budget about **60–90 minutes** the first time.

---

## What you're actually deploying

The demo does one clean loop:

1. You (admin) run `/setup-onboarding` in your onboarding channel → Zima posts a **welcome card with a "Get started" button**.
2. When a new person joins, Zima pings them in that channel and points them at the button.
3. They click **Get started** → a form pops up (name, location, skills, about, links).
4. On submit, Zima **saves their profile to your database** and gives them the **Vetted** role — which is what unlocks the rest of your server.

That's the whole demo. Matching, manifesto gates, and skill/mission roles are the *bigger* Zima vision — deliberately **not** in this build. This one exists to prove the join → profile → role loop works end to end.

### The three pieces

| Piece | What it is | Cost |
|---|---|---|
| **Discord app** | The bot identity + permissions | Free |
| **Supabase** | The database where profiles are stored | Free tier |
| **A place to run the bot** | Your Mac (for demoing) or Railway (always-on) | Free–$5/mo |

---

## Before you start — accounts you'll need

- A Discord account where you're **admin of the server** you're adding Zima to.
- A free **Supabase** account → [supabase.com](https://supabase.com)
- (For always-on hosting only) a free **Railway** account → [railway.app](https://railway.app)
- The `ZIMA/` folder on your computer (you already have it).

You do **not** need GitHub for the local demo. You'll only need it if you deploy to Railway (Part 6, Option B).

---

## Part 0 — One-time: make sure Node is installed

The bot runs on Node.js. Open the **Terminal** app and paste:

```
node --version
```

- If it prints something like `v18...`, `v20...`, or `v22...` → you're good, skip to Part 1.
- If it says "command not found" → install Node from [nodejs.org](https://nodejs.org) (get the "LTS" version), then re-run the check.

Then, one time, install the bot's dependencies. In Terminal:

```
cd "path/to/ZIMA"
npm install
```

> Tip: instead of typing the path, type `cd ` (with a space) and drag the `ZIMA` folder onto the Terminal window, then press Enter.

You should see it finish without red errors. (If `node_modules` already exists, `npm install` just confirms everything's present.)

---

## Part 1 — Set up the database (Supabase)

**1.1 — Create the project**
1. Go to [supabase.com](https://supabase.com) → sign in → **New project**.
2. Name it `zima-demo`. Set a database password (save it somewhere). Pick the region closest to you (Montreal → East US).
3. Wait ~2 minutes while it provisions.

**1.2 — Create the tables**
1. In the left sidebar → **SQL Editor** → **New query**.
2. Open the file `supabase/schema.sql` (inside this folder), copy **everything** in it, paste into the editor.
3. Click **Run**. You should see success, no errors.
4. Sidebar → **Table Editor** → confirm you now have three tables: **`profiles`**, **`role_grants`**, **`quest_completions`**.

**1.3 — Copy your two Supabase secrets**
1. Sidebar → **Project Settings** (gear) → **API**.
2. Copy the **Project URL** (looks like `https://abcxyz.supabase.co`) — you'll paste it as `SUPABASE_URL`.
3. Under **Project API keys**, copy the **`service_role`** key (NOT the `anon` key) — you'll paste it as `SUPABASE_SERVICE_ROLE_KEY`.

> ⚠️ The `service_role` key can read and write everything. Treat it like a password. Never post it publicly or commit it to GitHub.

---

## Part 2 — Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → name it **Zima** → Create.
2. **General Information** tab → copy the **Application ID** → this is your `DISCORD_APPLICATION_ID`.
3. **Bot** tab → **Reset Token** → **Copy** → this is your `DISCORD_TOKEN`. (You only see it once; if you lose it, reset again.)
4. Still on the **Bot** tab → scroll to **Privileged Gateway Intents** → turn **ON** → **Server Members Intent** → **Save Changes**.

> This one intent is **required** — it's how Zima notices when someone joins. You do **not** need Presence Intent or Message Content Intent for this demo.

---

## Part 3 — Prepare your Discord server

**3.1 — Turn on Developer Mode** (so you can copy IDs)
Discord → **User Settings** → **Advanced** → toggle **Developer Mode** ON.

**3.2 — Grab your Server ID**
Right-click your **server icon** → **Copy Server ID** → this is `DISCORD_SERVER_ID`.

**3.3 — Pick/create the onboarding channel**
Use an existing channel or make one (e.g. `#welcome`). Right-click the channel → **Copy Channel ID** → this is `ONBOARDING_CHANNEL_ID`.

**3.4 — Create the "Vetted" role**
1. **Server Settings** → **Roles** → **Create Role** → name it **Vetted** (this is the role new members earn by completing the form).
2. Right-click the role (or open it) → **Copy Role ID** → this is `VETTED_ROLE_ID`.

**3.5 — Invite the bot to your server**
1. Developer Portal → your app → **OAuth2** → **URL Generator**.
2. **Scopes:** check `bot` **and** `applications.commands`.
3. **Bot Permissions:** check **Manage Roles**, **Send Messages**, **View Channels**.
4. Copy the generated URL at the bottom → open it in your browser → pick your server → **Authorize**.
5. Confirm **Zima now appears in your server's member list** (it'll be offline/grey until you start it — that's expected).

**3.6 — Fix the role order (important!)**
Server Settings → **Roles** → **drag the Zima role ABOVE the Vetted role.**

> A bot can only hand out roles that sit *below* its own. If Vetted is above Zima, the profile saves but the role won't apply — and that's the #1 thing that goes wrong. Do this now.

---

## Part 4 — Fill in the configuration file

By now you've collected 7 values. You'll drop them into one file.

1. In the `ZIMA` folder, find **`.env.example`**. Make a copy of it and rename the copy to exactly **`.env`** (nothing before the dot).
   - Quick Terminal way: `cd "path/to/ZIMA"` then `cp .env.example .env`
2. Open `.env` in any text editor and fill in each blank:

```
DISCORD_TOKEN=            ← Part 2, step 3
DISCORD_APPLICATION_ID=   ← Part 2, step 2
DISCORD_SERVER_ID=        ← Part 3.2
ONBOARDING_CHANNEL_ID=    ← Part 3.3
VETTED_ROLE_ID=           ← Part 3.4
SUPABASE_URL=             ← Part 1.3
SUPABASE_SERVICE_ROLE_KEY=← Part 1.3
```

Paste each value right after the `=`, no quotes, no spaces. Save the file.

> `.env` is already listed in `.gitignore`, so it won't get uploaded if you later push to GitHub. Keep it that way.

---

## Part 5 — Register the slash command

This tells Discord that `/setup-onboarding` exists. Run it once (and again any time you change commands). In Terminal, from the `ZIMA` folder:

```
npm run register-commands
```

Success looks like: `Registered 1 command(s).`
Because you set `DISCORD_SERVER_ID`, the command appears in your server **within seconds**.

---

## Part 6 — Start the bot

Pick **one** path.

### Option A — Run on your Mac (best for demoing right now)
In Terminal, from the `ZIMA` folder:

```
npm run dev
```

You should see: `Zima logged in as Zima#0000`. In Discord, **Zima turns green (online).**

The catch: the bot only runs **while this Terminal window stays open**. Perfect for a live demo. Close the window and Zima goes offline. When you're done, press `Ctrl + C` to stop it.

### Option B — Host on Railway (always-on)
For a bot that stays online 24/7 without your Mac:

1. Put this project on **GitHub** (a private repo is fine).
2. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pick the repo.
3. Railway auto-detects Node and uses the `npm start` script.
4. Open the service → **Variables** → **Raw Editor** → paste the **same 7 lines** from your `.env`. Save.
5. Railway builds and deploys (~2 min). Open **Deploy Logs** — you want to see `Zima logged in as Zima#0000`.
6. Run `npm run register-commands` **once from your Mac** (Part 5) so the slash command is registered — you only need to do this a single time, not on every deploy.

---

## Part 7 — Turn it on and test the full loop

1. In Discord, go to your **onboarding channel** and type `/setup-onboarding` → send.
   - Zima replies privately "Onboarding message posted" and drops a **welcome card with a "Get started" button** in the channel. (Do this once; the card stays.)
2. Click **Get started** yourself → the profile form opens → fill it in → **Submit**.
3. You should get a private "Your profile is saved… you've been given the **Vetted** role" message, and see the **Vetted** role on your name.
4. **Test the join ping (optional):** have a friend (or a second/alt account) join the server. Zima should ping them in the onboarding channel pointing at the button. They complete the form → they get Vetted too.

---

## Part 8 — Confirm the data landed

Supabase → **Table Editor** → **`profiles`**. You should see a row with the name, location, skills, bio, and links you submitted, plus an `onboarding_completed_at` timestamp. The **`role_grants`** table logs that the Vetted role was given. That's proof the whole loop works.

---

## Troubleshooting (matched to the bot's own error messages)

**"Zima won't turn green / crashes on start with 'disallowed intents'"**
→ Part 2, step 4 wasn't saved. Turn ON **Server Members Intent** in the Developer Portal → Bot tab → Save. Restart.

**Registering commands fails with "Missing Access (50001)"**
→ The bot isn't actually in the server, or your IDs are from a different app. Recheck that `DISCORD_APPLICATION_ID` and `DISCORD_TOKEN` are from the **same** application, that `DISCORD_SERVER_ID` is correct, and that Zima shows in the member list. Then re-run `npm run register-commands`.

**Someone submits the form, profile saves, but they don't get the Vetted role**
→ Almost always the **role order**. The Zima role must sit **above** Vetted (Part 3.6). Zima will actually tell the user this in its reply. Also confirm the bot was invited with the **Manage Roles** permission.

**"Missing required environment variable"**
→ A blank in `.env`. Every one of the 7 lines needs a value after the `=`. Re-check Part 4.

**The `/setup-onboarding` command doesn't appear when I type `/`**
→ You skipped Part 5, or it registered globally. Run `npm run register-commands` with `DISCORD_SERVER_ID` set — that makes it appear instantly.

**Data isn't saving to Supabase**
→ You're using the `anon` key instead of `service_role` (Part 1.3), or the free Supabase project paused after inactivity — open the dashboard to wake it.

---

## Appendix A — What every setting is

| Variable | Where you got it | Required? |
|---|---|---|
| `DISCORD_TOKEN` | Dev Portal → Bot → Reset Token | Yes |
| `DISCORD_APPLICATION_ID` | Dev Portal → General Information → Application ID | Yes |
| `DISCORD_SERVER_ID` | Right-click server icon → Copy Server ID | Optional (makes commands instant) |
| `ONBOARDING_CHANNEL_ID` | Right-click channel → Copy Channel ID | Yes |
| `VETTED_ROLE_ID` | Server Settings → Roles → Vetted → Copy Role ID | Yes |
| `SUPABASE_URL` | Supabase → Settings → API → Project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API → service_role | Yes |

## Appendix B — What each file does

| File / folder | Purpose |
|---|---|
| `src/index.js` | Starts the bot, listens for joins and button/form clicks |
| `src/register-commands.js` | Registers the `/setup-onboarding` command |
| `src/features/onboarding/` | The welcome card, the profile form, and what happens on submit |
| `src/roles/roleManager.js` | Grants the Vetted role (with clear errors if it can't) |
| `src/db/supabase.js` | Reads/writes profiles and role grants |
| `src/config.js` | Loads your `.env` values |
| `supabase/schema.sql` | The database tables (run once in Supabase) |
| `.env` | Your 7 secrets (never share) |
| `_legacy_serverless/` | Old, unused experiment — ignore it |

## Appendix C — Commands cheat sheet

```
npm install               # one-time: install dependencies
npm run register-commands # register /setup-onboarding (once, and after command changes)
npm run dev               # run locally with auto-restart (demo)
npm start                 # run locally, production style
```

---

## Where this goes next (not in the demo)

The code is built to grow. The database already has a `quest_completions` table and the role system already logs every grant in `role_grants` — the scaffolding for **quest-based roles** later. When you're ready, the fuller Zima vision (manifesto/rules gates, skill + mission roles, and `/zima call` matching) layers on top of exactly this foundation. Prove the loop first with this demo, then expand.

🤞
