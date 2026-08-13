import { config } from '../config.js';

// Single client for the Python API. The bot is a trusted service: write paths
// authenticate with the X-Bot-Key header (BOT_API_KEY). This replaces the bot's
// former direct Supabase service-role access, so the Discord process no longer
// holds admin DB credentials — everything goes through the API's validation,
// one source of truth. Uses global fetch (Node 18+).

export class ApiError extends Error {}

async function apiFetch(path, { method = 'GET', body, auth = false, notFoundAsNull = false } = {}) {
  if (!config.apiBaseUrl) throw new ApiError('API_BASE_URL is not configured.');
  if (auth && !config.botApiKey) throw new ApiError('BOT_API_KEY is not configured.');

  const headers = { 'Content-Type': 'application/json' };
  if (auth) headers['X-Bot-Key'] = config.botApiKey;

  let res;
  try {
    res = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError(`Network error calling ${path}: ${err.message}`);
  }
  if (notFoundAsNull && res.status === 404) return null;
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(`API ${res.status} on ${path}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

// ── Profiles / roles (onboarding) ──

export const getProfileByDiscordId = (discordId) =>
  apiFetch(`/api/v1/bot/profiles/by-discord/${encodeURIComponent(discordId)}`, {
    auth: true,
    notFoundAsNull: true,
  });

export const upsertProfile = (profile) =>
  apiFetch('/api/v1/bot/profiles/upsert', { method: 'POST', auth: true, body: profile });

export const recordRoleGrant = ({ discordId, roleKey, source = 'system', metadata = {} }) =>
  apiFetch('/api/v1/bot/role-grants', {
    method: 'POST',
    auth: true,
    body: { discord_id: discordId, role_key: roleKey, source, metadata },
  });

// ── Neurotype quiz ──

export const getQuiz = (version = 'v1') =>
  apiFetch(`/api/v1/quiz?version=${encodeURIComponent(version)}`);

export const getNeurotypes = () => apiFetch('/api/v1/neurotypes');

export const submitQuiz = (discordId, answers, version = 'v1') =>
  apiFetch('/api/v1/bot/quiz/submit', {
    method: 'POST',
    auth: true,
    body: { discord_id: discordId, answers, version },
  });

export const setIdentified = (discordId, neurotype) =>
  apiFetch('/api/v1/bot/profiles/identified', {
    method: 'POST',
    auth: true,
    body: { discord_id: discordId, neurotype },
  });

// ── XP / gamification ──

// Read a builder's XP standing (total, level, progress, unlocked tiers). XP is
// only ever awarded server-side off real actions — the bot never posts XP, it
// only reads it for the /xp command.
export const getXp = (discordId) =>
  apiFetch(`/api/v1/bot/xp/${encodeURIComponent(discordId)}`, { auth: true });
