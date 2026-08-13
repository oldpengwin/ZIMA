import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../lib/auth.jsx';
import { PageLoader } from '../components/Loader.jsx';

// The backend redirects here after Discord OAuth with the token in the URL.
// With HashRouter that lands as `/#/auth/callback?access_token=...`, so the
// token stays in the fragment (never sent to a server) and useSearchParams
// reads it.
export default function AuthCallback() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const err = params.get('error');
    const token = params.get('access_token');
    if (err) {
      setError(err);
    } else if (token) {
      login(token);
      navigate('/me', { replace: true });
    } else {
      setError('No token was returned from the login.');
    }
  }, [params, login, navigate]);

  if (error) {
    return (
      <div className="section">
        <div className="notice error">Login failed: {error}</div>
      </div>
    );
  }
  return (
    <div className="section">
      <PageLoader label="Finishing sign-in…" />
    </div>
  );
}
