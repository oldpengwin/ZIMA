import { config } from '../../config.js';

// Thin client for the Python API. The bot is a trusted service: it authenticates
// the write paths with the X-Bot-Key header (BOT_API_KEY). Uses global fetch
// (Node 18+). All scoring lives server-side — the bot never sees the weights.

class ApiError extends Error {}

async function apiFetch(path, { method = 'GET', body, auth = false } = {}) {
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
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(`API ${res.status} on ${path}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

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
