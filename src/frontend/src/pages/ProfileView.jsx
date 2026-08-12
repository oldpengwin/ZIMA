import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';
import NeurotypeBadge from '../components/NeurotypeBadge.jsx';
import { PageLoader } from '../components/Loader.jsx';

export default function ProfileView() {
  const { id } = useParams();
  const { profile: me } = useAuth();
  const [p, setP] = useState(null);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState('');
  const [connState, setConnState] = useState('idle'); // idle | sending | sent | error
  const [connErr, setConnErr] = useState(null);

  useEffect(() => {
    setP(null);
    setError(null);
    api.getProfile(id).then(setP).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="section"><div className="notice error">{error}</div></div>;
  if (!p) return <div className="section"><PageLoader /></div>;

  const isMe = me && me.id === p.id;

  const connect = async () => {
    setConnState('sending');
    setConnErr(null);
    try {
      await api.requestConnection({ toUserId: p.id, message: msg.trim() });
      setConnState('sent');
    } catch (e) {
      setConnErr(e.message);
      setConnState('error');
    }
  };

  return (
    <div className="section" style={{ maxWidth: 680 }}>
      <SectionFlag n={4}>BUILDER</SectionFlag>
      <div className="spread" style={{ margin: '8px 0 12px' }}>
        <h2 className="display h2" style={{ margin: 0 }}>{p.display_name}</h2>
        {isMe && <Link to="/me" className="btn btn-sm">Edit yours</Link>}
      </div>
      {p.location && <div className="label" style={{ marginBottom: 14 }}>{p.location}</div>}

      <div className="row" style={{ marginBottom: 16 }}>
        {p.identified_neurotype && <NeurotypeBadge type={p.identified_neurotype} kind="identifies as" />}
        {p.assessed_neurotype && p.assessed_neurotype !== p.identified_neurotype && (
          <NeurotypeBadge type={p.assessed_neurotype} kind="assessed" />
        )}
      </div>

      {p.tagline && <p style={{ fontSize: '1.08rem' }}>{p.tagline}</p>}
      {p.bio && <p className="muted">{p.bio}</p>}

      {p.skills?.length > 0 && (
        <div className="row" style={{ gap: 6, margin: '16px 0' }}>
          {p.skills.map((s) => <span key={s} className="tag">{s}</span>)}
        </div>
      )}
      {p.links?.length > 0 && (
        <div className="stack" style={{ gap: 4, marginBottom: 8 }}>
          {p.links.map((l) => (
            <a key={l} href={l} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', wordBreak: 'break-all' }}>{l}</a>
          ))}
        </div>
      )}

      {!isMe && (
        <div className="panel" style={{ marginTop: 20 }}>
          <div className="label" style={{ marginBottom: 8 }}>Reach out</div>
          {connState === 'sent' ? (
            <div className="notice ok">Connection request sent to {p.display_name}.</div>
          ) : (
            <>
              <textarea
                className="textarea"
                value={msg}
                onChange={(e) => setMsg(e.target.value)}
                placeholder={`Why do you want to connect with ${p.display_name}?`}
              />
              {connErr && <div className="notice error" style={{ margin: '10px 0' }}>{connErr}</div>}
              <button className="btn btn-lime" style={{ marginTop: 10 }} onClick={connect} disabled={connState === 'sending'}>
                {connState === 'sending' ? 'Sending…' : 'Request connection'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
