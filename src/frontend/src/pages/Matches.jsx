import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';
import ProfileCard from '../components/ProfileCard.jsx';
import { Spinner } from '../components/Loader.jsx';

export default function Matches() {
  const { profile: me } = useAuth();
  const [matches, setMatches] = useState(null);
  const [matchErr, setMatchErr] = useState(null);
  const [requests, setRequests] = useState(null);
  const [reqErr, setReqErr] = useState(null);

  const loadRequests = useCallback(async () => {
    try {
      const data = await api.getConnectionRequests(me.id);
      const incoming = (data.requests || []).filter((c) => c.to_user_id === me.id && c.status === 'pending');
      const withProfiles = await Promise.all(
        incoming.map(async (c) => {
          let from = null;
          try {
            from = await api.getProfile(c.from_user_id);
          } catch {
            /* keep null */
          }
          return { ...c, from };
        }),
      );
      setRequests(withProfiles);
    } catch (e) {
      setReqErr(e.message);
      setRequests([]);
    }
  }, [me.id]);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getMatches(me.id);
        const enriched = await Promise.all(
          (data.matches || []).map(async (m) => {
            let profile = null;
            try {
              profile = await api.getProfile(m.profile_id);
            } catch {
              /* keep null */
            }
            return { ...m, profile };
          }),
        );
        setMatches(enriched.filter((m) => m.profile));
      } catch (e) {
        setMatchErr(e.message);
        setMatches([]);
      }
    })();
    loadRequests();
  }, [me.id, loadRequests]);

  const respond = async (connId, status) => {
    try {
      await api.respondToConnection(connId, status);
      await loadRequests();
    } catch (e) {
      setReqErr(e.message);
    }
  };

  return (
    <div className="section">
      <SectionFlag n={5}>MATCHES</SectionFlag>
      <h2 className="display h2" style={{ margin: '8px 0 6px' }}>WHO YOU SHOULD MEET</h2>
      <p className="muted" style={{ marginTop: 0, marginBottom: 20 }}>Ranked by how you think, not what you type.</p>

      {matches === null ? (
        <Spinner label="Finding matches…" />
      ) : matchErr ? (
        <div className="notice error">
          {/quiz/i.test(matchErr) ? (
            <>Take the <Link to="/quiz" style={{ color: 'var(--cyan)' }}>typology quiz</Link> first to unlock matches.</>
          ) : (
            matchErr
          )}
        </div>
      ) : matches.length === 0 ? (
        <div className="empty">No matches yet — as more builders join, they'll appear here.</div>
      ) : (
        <div className="grid cards">
          {matches.map((m) => (
            <div key={m.profile_id} style={{ position: 'relative' }}>
              <span
                className="pill"
                style={{ position: 'absolute', top: 10, right: 10, zIndex: 2, background: 'var(--charcoal)', borderColor: 'var(--lime)', color: 'var(--lime)' }}
              >
                {Math.round((m.score || 0) * 100)}% fit
              </span>
              <ProfileCard profile={m.profile} />
            </div>
          ))}
        </div>
      )}

      <hr className="divider" style={{ margin: '34px 0' }} />
      <SectionFlag n={6}>REQUESTS</SectionFlag>
      <h3 className="display h3" style={{ margin: '8px 0 16px' }}>INCOMING</h3>
      {requests === null ? (
        <Spinner />
      ) : reqErr ? (
        <div className="notice error">{reqErr}</div>
      ) : requests.length === 0 ? (
        <div className="empty">No pending connection requests.</div>
      ) : (
        <div className="stack">
          {requests.map((c) => (
            <div key={c.id} className="panel spread">
              <div>
                <strong>{c.from?.display_name || 'A builder'}</strong>
                {c.from?.location && <span className="muted"> · {c.from.location}</span>}
                {c.message && <p className="muted" style={{ margin: '6px 0 0' }}>“{c.message}”</p>}
              </div>
              <div className="row">
                <button className="btn btn-lime btn-sm" onClick={() => respond(c.id, 'accepted')}>Accept</button>
                <button className="btn btn-danger btn-sm" onClick={() => respond(c.id, 'rejected')}>Decline</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
