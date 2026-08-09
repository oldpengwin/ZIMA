# Zima

Discord bot for member onboarding: collect a profile, save it to Supabase, and grant the **Vetted** role. Built with room to grow into quest-based role rewards later.

## What it does

1. An admin runs `/setup-onboarding` in your onboarding channel — Zima posts a welcome embed with a **Get started** button.
2. New members get a ping in that channel when they join (until they finish onboarding).
3. **Get started** opens a modal (name, location, skills, bio, links). Discord username is captured automatically.
4. On submit, the profile is upserted in Supabase, a `role_grants` row is recorded, and the **Vetted** role is assigned.

## Setup

### 1. Discord application

1. [Discord Developer Portal](https://discord.com/developers/applications) → your app → **Bot** → copy **Token** → `DISCORD_TOKEN`.
2. **General Information** → copy **Application ID** → `DISCORD_APPLICATION_ID`. (You do **not** need **Public Key** — that is only for HTTP/webhook bots, not Zima.)
3. Enable **Server Members Intent** under Privileged Gateway Intents.
4. Invite the bot with permissions: `Manage Roles`, `Send Messages`, `Use Slash Commands`, `View Channels`.
5. In your Discord server: create a **Vetted** role and place the bot’s role **above** it.
6. Create an onboarding channel; copy its ID (Developer Mode → right‑click channel → **Copy Channel ID**).

### 2. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Run `supabase/schema.sql` in the SQL editor.
3. Copy **Project URL** and **service_role** key (Settings → API). Use the service role only on the server, never in the client.

### 3. Environment

```bash
cd zima-bot
cp .env.example .env
# fill in all values
npm run register-commands
```

4. **Required before `npm run dev`:** **Bot** → **Privileged Gateway Intents** → enable **SERVER MEMBERS INTENT** → **Save**. Without this, the bot crashes with `Used disallowed intents`.
5. Invite the bot: **OAuth2 → URL Generator** → scopes **`bot`** + **`applications.commands`** → permissions **Manage Roles**, **Send Messages**, **View Channels** → open URL and add to your server. The bot must appear in the member list before `npm run register-commands` works.

In your onboarding channel, run `/setup-onboarding` once.

## Environment variables

| Variable | Where to find it in Discord |
|----------|-----------------------------|
| `DISCORD_TOKEN` | Developer Portal → **Bot** → Token |
| `DISCORD_APPLICATION_ID` | Developer Portal → **General Information** → Application ID |
| `DISCORD_SERVER_ID` | Your server icon → **Copy Server ID** (Developer Mode on). Optional; speeds up slash command registration. |
| `ONBOARDING_CHANNEL_ID` | Onboarding channel → **Copy Channel ID** |
| `VETTED_ROLE_ID` | **Server Settings** → **Roles** → Vetted role → **Copy Role ID** |
| `SUPABASE_URL` | Supabase → Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API → `service_role` |

**Not used by Zima:** `PUBLIC_KEY`, `APP_ID` (from the old `discord-example-app` webhook sample).

Legacy names still work if your `.env` already has them: `DISCORD_CLIENT_ID` → application ID, `DISCORD_GUILD_ID` → server ID.

## Future: quests and role progression

- `role_grants` logs every role Zima assigns (onboarding today; quests later).
- `quest_completions` is ready for tracking finished quests.
- Extend `roleKeys` and `questRoleMap` in `src/config.js` and `src/roles/roleManager.js` to grant new roles when quests complete.

## Scripts

- `npm run dev` — run with file watch
- `npm start` — production run
- `npm run register-commands` — register slash commands
