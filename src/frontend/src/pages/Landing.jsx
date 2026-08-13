import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';

export default function Landing() {
  const { isAuthed, hasProfile, devLogin } = useAuth();
  const navigate = useNavigate();
  const [devId, setDevId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (isAuthed) return <Navigate to={hasProfile ? '/discover' : '/onboarding'} replace />;

  const handleDev = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await devLogin(devId.trim() || String(Date.now()), 'dev');
      navigate('/onboarding');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="section">
      <SectionFlag n={0}>ENTER</SectionFlag>

      <div style={{ maxWidth: 780, padding: '26px 0 10px' }}>
        <p className="script" style={{ fontSize: '1.9rem', margin: '0 0 2px' }}>find your people,</p>
        <h1 className="display h1">
          THE BUILDERS<br />NETWORK.
        </h1>
        <p className="muted" style={{ fontSize: '1.06rem', maxWidth: 540, marginTop: 18 }}>
          Take the typology. Get your archetype. Meet the humans building the same future — matched by how
          you actually think, not by keywords.
        </p>
        <div className="row" style={{ marginTop: 26 }}>
          <a className="btn btn-primary btn-lg" href={api.discordLoginUrl()}>
            Continue with Discord
          </a>
        </div>
      </div>

      <div className="panel" style={{ maxWidth: 460, marginTop: 44 }}>
        <div className="label" style={{ marginBottom: 8 }}>Local dev login</div>
        <p className="hint" style={{ marginTop: 0 }}>
          For testing without Discord OAuth. Works only while the backend runs outside production.
        </p>
        <form onSubmit={handleDev}>
          <div className="field">
            <label htmlFor="devid">Discord ID (any number, or leave blank)</label>
            <input
              id="devid"
              className="input"
              value={devId}
              onChange={(e) => setDevId(e.target.value)}
              placeholder="123456789012345678"
              inputMode="numeric"
            />
          </div>
          {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
          <button className="btn" disabled={busy}>{busy ? 'Signing in…' : 'Dev sign in'}</button>
        </form>
      </div>
    </div>
  );
}
