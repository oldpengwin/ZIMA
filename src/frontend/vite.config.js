import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, `/api/*` is proxied to the FastAPI backend so the frontend can use
// relative URLs (no CORS dance locally). In production set VITE_API_URL to the
// deployed API origin (see src/lib/api.js).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
