import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';
import NeurotypeBadge from '../components/NeurotypeBadge.jsx';

const toArray = (s) => (s || '').split(',').map((x) => x.trim()).filter(Boolean);
const fromArray = (a) => (a || []).join(', ');

export default function ProfileMe() {
  const { profile: me, refresh, logout } = useAuth();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => ({
    display_name: me.display_name || '',
    location: me.location || '',
    tagline: me.tagline || '',
    bio: me.bio || '',
    skills: fromArray(me.skills),
    links: fromArray(me.links),
  }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.updateProfile(me.id, {
        display_name: form.display_name.trim(),
        location: form.location.trim() || null,
        tagline: form.tagline.trim() || null,
        bio: form.bio.trim() || null,
        skills: toArray(form.skills),
        links: toArray(form.links),
      });
      await refresh();
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleOpen = async () => {
    setBusy(true);
    try {
      await api.updateProfile(me.id, { is_open: !me.is_open });
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const exportData = async () => {
    try {
      const data = await api.exportMe();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'zima-my-data.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const deleteAccount = async () => {
    setBusy(true);
    try {
      await api.deleteMe();
      logout();
      navigate('/');
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="section" style={{ maxWidth: 660 }}>
      <SectionFlag n={4}>YOUR PROFILE</SectionFlag>

      {editing ? (
        <form onSubmit={save} className="panel" style={{ marginTop: 10 }}>
          <div className="field">
            <label htmlFor="dn">Name</label>
            <input id="dn" className="input" value={form.display_name} onChange={set('display_name')} maxLength={100} required />
          </div>
          <div className="field">
            <label htmlFor="lo">Location</label>
            <input id="lo" className="input" value={form.location} onChange={set('location')} maxLength={100} />
          </div>
          <div className="field">
            <label htmlFor="tg">Tagline</label>
            <input id="tg" className="input" value={form.tagline} onChange={set('tagline')} maxLength={255} />
          </div>
          <div className="field">
            <label htmlFor="bi">About you</label>
            <textarea id="bi" className="textarea" value={form.bio} onChange={set('bio')} />
          </div>
          <div className="field">
            <label htmlFor="sk">Skills (comma-separated)</label>
            <input id="sk" className="input" value={form.skills} onChange={set('skills')} />
          </div>
          <div className="field">
            <label htmlFor="li">Links (comma-separated)</label>
            <input id="li" className="input" value={form.links} onChange={set('links')} />
          </div>
          {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
          <div className="row">
            <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
            <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <>
          <div className="spread" style={{ margin: '8px 0 12px' }}>
            <h2 className="display h2" style={{ margin: 0 }}>{me.display_name}</h2>
            <button className="btn btn-sm" onClick={() => setEditing(true)}>Edit</button>
          </div>
          {me.location && <div className="label" style={{ marginBottom: 14 }}>{me.location}</div>}

          <div className="row" style={{ marginBottom: 16 }}>
            {me.identified_neurotype && <NeurotypeBadge type={me.identified_neurotype} kind="you identify as" />}
            {me.assessed_neurotype && <NeurotypeBadge type={me.assessed_neurotype} kind="assessed" />}
            {!me.identified_neurotype && !me.assessed_neurotype && (
              <Link className="btn btn-sm btn-lime" to="/quiz">Take the typology →</Link>
            )}
          </div>

          {me.tagline && <p style={{ fontSize: '1.05rem' }}>{me.tagline}</p>}
          {me.bio && <p className="muted">{me.bio}</p>}
          {me.skills?.length > 0 && (
            <div className="row" style={{ gap: 6, margin: '14px 0' }}>
              {me.skills.map((s) => <span key={s} className="tag">{s}</span>)}
            </div>
          )}

          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn btn-sm" onClick={toggleOpen} disabled={busy}>
              {me.is_open ? 'Open to connect ✓' : 'Not looking'}
            </button>
            {(me.identified_neurotype || me.assessed_neurotype) && (
              <Link className="btn btn-sm btn-ghost" to="/quiz">Retake typology</Link>
            )}
          </div>
        </>
      )}

      <div className="panel" style={{ marginTop: 26 }}>
        <div className="label" style={{ marginBottom: 10 }}>Your data</div>
        <div className="row">
          <button className="btn btn-sm" onClick={exportData}>Export my data</button>
          {!confirmDelete ? (
            <button className="btn btn-sm btn-danger" onClick={() => setConfirmDelete(true)}>Delete account</button>
          ) : (
            <>
              <span className="muted" style={{ fontSize: '0.85rem' }}>Permanent — no undo.</span>
              <button className="btn btn-sm btn-danger" onClick={deleteAccount} disabled={busy}>Confirm delete</button>
              <button className="btn btn-sm btn-ghost" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </>
          )}
        </div>
        {error && !editing && <div className="notice error" style={{ marginTop: 12 }}>{error}</div>}
      </div>
    </div>
  );
}
