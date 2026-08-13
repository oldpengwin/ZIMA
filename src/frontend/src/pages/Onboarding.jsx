import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';

const toArray = (s) => (s || '').split(',').map((x) => x.trim()).filter(Boolean);

export default function Onboarding() {
  const { hasProfile, refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ display_name: '', location: '', skills: '', tagline: '', bio: '', links: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (hasProfile) return <Navigate to="/me" replace />;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.display_name.trim()) {
      setError('A name is required.');
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await api.createProfile({
        display_name: form.display_name.trim(),
        location: form.location.trim() || null,
        skills: toArray(form.skills),
        tagline: form.tagline.trim() || null,
        bio: form.bio.trim() || null,
        links: toArray(form.links),
      });
      await refresh();
      navigate('/quiz');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="section" style={{ maxWidth: 620 }}>
      <SectionFlag n={1}>YOUR PROFILE</SectionFlag>
      <h2 className="display h2" style={{ margin: '10px 0 6px' }}>WHO ARE YOU<br />BUILDING AS?</h2>
      <p className="muted" style={{ marginTop: 0, marginBottom: 24 }}>
        The basics now — you'll get your archetype from the typology next.
      </p>

      <form onSubmit={submit} className="panel">
        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" className="input" value={form.display_name} onChange={set('display_name')} maxLength={100} required />
        </div>
        <div className="field">
          <label htmlFor="loc">Location (city / region)</label>
          <input id="loc" className="input" value={form.location} onChange={set('location')} maxLength={100} placeholder="e.g. Lagos" />
        </div>
        <div className="field">
          <label htmlFor="skills">Skills (comma-separated)</label>
          <input id="skills" className="input" value={form.skills} onChange={set('skills')} placeholder="design, python, community" />
        </div>
        <div className="field">
          <label htmlFor="tag">Tagline</label>
          <input id="tag" className="input" value={form.tagline} onChange={set('tagline')} maxLength={255} placeholder="One line on what you're about" />
        </div>
        <div className="field">
          <label htmlFor="bio">About you</label>
          <textarea id="bio" className="textarea" value={form.bio} onChange={set('bio')} placeholder="A few sentences." />
        </div>
        <div className="field">
          <label htmlFor="links">Links (comma-separated)</label>
          <input id="links" className="input" value={form.links} onChange={set('links')} placeholder="https://…, https://…" />
        </div>
        {error && <div className="notice error" style={{ marginBottom: 14 }}>{error}</div>}
        <button className="btn btn-primary btn-lg" disabled={busy}>
          {busy ? 'Saving…' : 'Save & take the typology'}
        </button>
      </form>
    </div>
  );
}
