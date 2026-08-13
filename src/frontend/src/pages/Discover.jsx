import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import SectionFlag from '../components/SectionFlag.jsx';
import ProfileCard from '../components/ProfileCard.jsx';
import { Spinner } from '../components/Loader.jsx';

export default function Discover() {
  const [q, setQ] = useState('');
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async (query) => {
    setLoading(true);
    setError(null);
    try {
      // backend requires q length >= 2; blank lists everyone
      setProfiles(await api.searchProfiles({ q: query && query.length >= 2 ? query : undefined }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load('');
  }, []);

  const onSubmit = (e) => {
    e.preventDefault();
    load(q.trim());
  };

  return (
    <div className="section">
      <SectionFlag n={3}>DISCOVER</SectionFlag>
      <h2 className="display h2" style={{ margin: '8px 0 18px' }}>FIND YOUR PEOPLE</h2>
      <form onSubmit={onSubmit} className="row" style={{ marginBottom: 24, gap: 8 }}>
        <input
          className="input"
          style={{ maxWidth: 380 }}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, skill, location…"
        />
        <button className="btn btn-primary">Search</button>
        {q && (
          <button type="button" className="btn btn-ghost" onClick={() => { setQ(''); load(''); }}>Clear</button>
        )}
      </form>

      {loading ? (
        <Spinner label="Loading builders…" />
      ) : error ? (
        <div className="notice error">{error}</div>
      ) : profiles.length === 0 ? (
        <div className="empty">No builders match that yet.</div>
      ) : (
        <div className="grid cards">
          {profiles.map((p) => (
            <ProfileCard key={p.id} profile={p} />
          ))}
        </div>
      )}
    </div>
  );
}
