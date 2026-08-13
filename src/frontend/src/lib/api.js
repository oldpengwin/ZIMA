// Client for the real FastAPI backend. In dev, calls are relative (`/api/v1/...`)
// and Vite proxies them to the backend; in prod set VITE_API_URL to the API
// origin. JWT is attached as a Bearer token on every request once set.

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

let authToken = null;
export function setAuthToken(token) {
  authToken = token || null;
}
export function getAuthToken() {
  return authToken;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, query } = {}) {
  let url = `${BASE}/api/v1${path}`;
  if (query) {
    const qs = new URLSearchParams(
      Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString();
    if (qs) url += `?${qs}`;
  }
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  let res;
  try {
    res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch (err) {
    throw new ApiError('Could not reach the server. Is the API running?', 0);
  }
  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) ||
      (Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join(', ') : null) ||
      `Request failed (${res.status})`;
    throw new ApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), res.status);
  }
  return data;
}

export const api = {
  base: BASE,

  // ── auth ──
  discordLoginUrl: () => `${BASE}/api/v1/auth/discord/login`,
  devToken: (discordId, username = 'dev-user') =>
    request('/auth/dev-token', { method: 'POST', query: { discord_id: discordId, username } }),

  // ── profiles ──
  createProfile: (data) => request('/profiles', { method: 'POST', body: data }),
  getMe: () => request('/profiles/me'),
  getProfile: (id) => request(`/profiles/${id}`),
  updateProfile: (id, updates) => request(`/profiles/${id}`, { method: 'PUT', body: updates }),
  searchProfiles: ({ q, limit = 24, offset = 0 } = {}) => request('/profiles', { query: { q, limit, offset } }),
  getProfileStats: (id) => request(`/profiles/${id}/stats`),

  // ── neurotype quiz ──
  getQuiz: () => request('/quiz'),
  submitQuiz: ({ answers, identified, version = 'v1' }) =>
    request('/quiz/submit', { method: 'POST', body: { answers, identified, version } }),
  setIdentified: (profileId, neurotype) =>
    request(`/profiles/${profileId}/identified-neurotype`, { method: 'PUT', body: { neurotype } }),

  // ── archetypes / network ──
  getNeurotypes: () => request('/neurotypes'),
  getNetwork: () => request('/network'),

  // ── matching / connections ──
  getMatches: (userId, limit = 8) => request(`/match/${userId}`, { query: { limit } }),
  requestConnection: ({ toUserId, message }) =>
    request('/match/request', { method: 'POST', body: { to_user_id: toUserId, message } }),
  getConnectionRequests: (userId) => request(`/match/${userId}/requests`),
  respondToConnection: (connectionId, status) =>
    request(`/match/requests/${connectionId}`, { method: 'PUT', body: { status } }),

  // ── projects ──
  listProjects: ({ status, limit = 24, offset = 0 } = {}) => request('/projects', { query: { status, limit, offset } }),
  createProject: (data) => request('/projects', { method: 'POST', body: data }),
  getProject: (id) => request(`/projects/${id}`),
  joinProject: (id, role = 'contributor') => request(`/projects/${id}/join`, { method: 'POST', body: { role } }),
  updateProject: (id, updates) => request(`/projects/${id}`, { method: 'PUT', body: updates }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),

  // ── organizations ──
  listOrganizations: ({ org_type, limit = 24, offset = 0 } = {}) =>
    request('/organizations', { query: { org_type, limit, offset } }),
  createOrganization: (data) => request('/organizations', { method: 'POST', body: data }),
  getOrganization: (id) => request(`/organizations/${id}`),
  updateOrganization: (id, updates) => request(`/organizations/${id}`, { method: 'PUT', body: updates }),
  deleteOrganization: (id) => request(`/organizations/${id}`, { method: 'DELETE' }),

  // ── privacy ──
  exportMe: () => request('/users/me/export'),
  deletionPreview: () => request('/users/me/deletion-preview'),
  deleteMe: () => request('/users/me', { method: 'DELETE' }),
};
