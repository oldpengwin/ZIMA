# ZIMA Frontend

A React (Vite) single-page app that runs on the **real FastAPI backend** — no
mocks. Login, profile, the typology quiz, discovery/search, matching, and the
archetype network all hit live `/api/v1` endpoints.

## Run locally

```bash
cd src/frontend
npm install
npm run dev          # http://localhost:3000
```

The dev server proxies `/api/*` to `http://localhost:8000` (the FastAPI backend),
so start the backend too. Point the proxy elsewhere with `VITE_API_PROXY`.

To use the app you need to be logged in:

- **Discord (real):** click *Continue with Discord*. Set `FRONTEND_URL=http://localhost:3000`
  on the **backend** so the OAuth callback redirects back here with your token.
- **Dev login (no Discord):** the landing page has a dev sign-in — it uses the
  backend's `dev-token` endpoint, which is hard-disabled outside development.

## Build & deploy

```bash
npm run build        # -> dist/
npm run preview      # preview the production build
```

Deploy `dist/` as static files (Vercel, Netlify, Cloudflare Pages, any host).
It uses `HashRouter`, so **no SPA rewrite config is needed**. For production set:

- `VITE_API_URL` = the deployed API origin (e.g. `https://api.zima.example`).
- On the backend, `FRONTEND_URL` = this app's deployed origin.

## Stack

Vite + React 18 + React Router 6. No CSS framework — the Hopamine brand design
system lives in `src/styles/global.css`. No `react-scripts` (and none of its
CVEs). API client: `src/lib/api.js`; auth: `src/lib/auth.jsx`.
