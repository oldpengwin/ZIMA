import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, setAuthToken } from './api.js';

// Token lives in sessionStorage (cleared when the tab closes). The real login
// is Discord OAuth2 (the backend redirects back with the token in the URL
// fragment — see pages/AuthCallback). devLogin() uses the dev-token endpoint,
// which the backend hard-disables outside development, for easy local testing.
const TOKEN_KEY = 'zima_token';
const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    try {
      setProfile(await api.getMe());
    } catch (err) {
      // 404 = authed but hasn't created a profile yet; 401 = bad/expired token.
      setProfile(null);
      return err.status;
    }
    return 200;
  }, []);

  useEffect(() => {
    setAuthToken(token);
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);

    let active = true;
    (async () => {
      if (token) await loadProfile();
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [token, loadProfile]);

  const login = useCallback((newToken) => {
    setLoading(true);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    sessionStorage.removeItem(TOKEN_KEY);
    setProfile(null);
    setToken(null);
  }, []);

  const devLogin = useCallback(
    async (discordId, username) => {
      const res = await api.devToken(discordId, username);
      login(res.access_token);
      return res.access_token;
    },
    [login],
  );

  const value = {
    token,
    profile,
    loading,
    isAuthed: !!token,
    hasProfile: !!profile,
    login,
    logout,
    devLogin,
    refresh: loadProfile,
    setProfile,
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
