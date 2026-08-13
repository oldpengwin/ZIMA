import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';
import { Spinner } from '../components/Loader.jsx';
import { safeLinks } from '../lib/url.js';

const ORG_TYPES = ['hardware', 'advocacy', 'employment', 'finance', 'infrastructure', 'research', 'education'];
const toArray = (s) => (s || '').split(',').map((x) => x.trim()).filter(Boolean);
const fromArray = (a) => (a || []).join(', ');

const emptyForm = {
  name: '', mission: '', location: '', org_type: '', roles_open: '', project_links: '', email: '', beta_info: '', resume_request: false,
};

function OrgForm({ initial, onCancel, onSave }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setBool = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.checked }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Name is required.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSave({
        name: form.name.trim(),
        mission: form.mission.trim() || null,
        location: form.location.trim() || null,
        org_type: form.org_type || null,
        roles_open: toArray(form.roles_open),
        project_links: toArray(form.project_links),
        email: form.email.trim() || null,
        beta_info: form.beta_info.trim() || null,
        resume_request: !!form.resume_request,
      });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="panel" style={{ marginBottom: 20 }}>
      <div className="field">
        <label htmlFor="on">Name</label>
        <input id="on" className="input" value={form.name} onChange={set('name')} maxLength={200} required />
      </div>
      <div className="field">
        <label htmlFor="om">Mission</label>
        <textarea id="om" className="textarea" value={form.mission} onChange={set('mission')} maxLength={5000} />
      </div>
      <div className="field">
        <label htmlFor="ol">Location</label>
        <input id="ol" className="input" value={form.location} onChange={set('location')} maxLength={100} />
      </div>
      <div className="field">
        <label htmlFor="ot">Type</label>
        <select id="ot" className="input" value={form.org_type} onChange={set('org_type')}>
          <option value="">—</option>
          {ORG_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="or">Roles open (comma-separated)</label>
        <input id="or" className="input" value={form.roles_open} onChange={set('roles_open')} />
      </div>
      <div className="field">
        <label htmlFor="opl">Project links (comma-separated URLs)</label>
        <input id="opl" className="input" value={form.project_links} onChange={set('project_links')} />
      </div>
      <div className="field">
        <label htmlFor="oe">Contact email</label>
        <input id="oe" className="input" type="email" value={form.email} onChange={set('email')} maxLength={255} />
      </div>
      <div className="field">
        <label htmlFor="ob">Beta info</label>
        <textarea id="ob" className="textarea" value={form.beta_info} onChange={set('beta_info')} maxLength={5000} />
      </div>
      <label className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 14 }}>
        <input type="checkbox" checked={!!form.resume_request} onChange={setBool('resume_request')} />
        <span>Accepting resumes</span>
      </label>
      {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="row">
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  );
}

function OrgCard({ org, isMine, onEdit, onDelete }) {
  return (
    <div className="card">
      <div className="spread" style={{ marginBottom: 8 }}>
        <strong style={{ fontSize: '1.05rem' }}>{org.name}</strong>
        {org.org_type && <span className="tag">{org.org_type}</span>}
      </div>
      {org.owner_deleted && <div className="label" style={{ marginBottom: 8 }}>owner account deleted</div>}
      {org.location && <div className="label" style={{ marginBottom: 8 }}>{org.location}</div>}
      {org.mission && <p className="muted" style={{ margin: '0 0 10px', fontSize: '0.9rem' }}>{org.mission}</p>}
      {org.roles_open?.length > 0 && (
        <div className="row" style={{ gap: 6, marginBottom: 10 }}>
          {org.roles_open.map((r) => <span key={r} className="tag">{r}</span>)}
        </div>
      )}
      {safeLinks(org.project_links).length > 0 && (
        <div className="stack" style={{ gap: 4, marginBottom: 10 }}>
          {safeLinks(org.project_links).map((l) => (
            <a key={l} href={l} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', fontSize: '0.85rem', wordBreak: 'break-all' }}>{l}</a>
          ))}
        </div>
      )}
      {org.resume_request && <div className="label" style={{ marginBottom: 10 }}>Accepting resumes</div>}
      {isMine && (
        <div className="row" style={{ gap: 8 }}>
          <button className="btn btn-sm" onClick={onEdit}>Edit</button>
          <button className="btn btn-sm btn-danger" onClick={onDelete}>Delete</button>
        </div>
      )}
    </div>
  );
}

export default function Organizations() {
  const { profile: me } = useAuth();
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState('');
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = async (org_type) => {
    setLoading(true);
    setError(null);
    try {
      setOrgs(await api.listOrganizations({ org_type: org_type || undefined, limit: 50 }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(typeFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeFilter]);

  const create = async (data) => {
    await api.createOrganization(data);
    setCreating(false);
    setNotice('Organization created.');
    await load(typeFilter);
  };

  const update = async (id, data) => {
    await api.updateOrganization(id, data);
    setEditingId(null);
    setNotice('Organization updated.');
    await load(typeFilter);
  };

  const remove = async (id) => {
    try {
      await api.deleteOrganization(id);
      setNotice('Organization deleted.');
      await load(typeFilter);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="section">
      <SectionFlag n={9}>ORGANIZE</SectionFlag>
      <div className="spread" style={{ margin: '8px 0 18px' }}>
        <h2 className="display h2" style={{ margin: 0 }}>ORGANIZATIONS</h2>
        {!creating && <button className="btn btn-primary" onClick={() => setCreating(true)}>New organization</button>}
      </div>

      {creating && (
        <OrgForm initial={emptyForm} onCancel={() => setCreating(false)} onSave={create} />
      )}

      <div className="row" style={{ marginBottom: 20, gap: 8, flexWrap: 'wrap' }}>
        <button
          className={`btn btn-sm${typeFilter === '' ? ' btn-lime' : ''}`}
          onClick={() => setTypeFilter('')}
        >
          All
        </button>
        {ORG_TYPES.map((t) => (
          <button
            key={t}
            className={`btn btn-sm${typeFilter === t ? ' btn-lime' : ''}`}
            onClick={() => setTypeFilter(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {notice && <div className="notice ok" style={{ marginBottom: 16 }}>{notice}</div>}
      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      {loading ? (
        <Spinner label="Loading organizations…" />
      ) : orgs.length === 0 ? (
        <div className="empty">No organizations yet.</div>
      ) : (
        <div className="grid cards">
          {orgs.map((o) =>
            editingId === o.id ? (
              <OrgForm
                key={o.id}
                initial={{
                  name: o.name,
                  mission: o.mission || '',
                  location: o.location || '',
                  org_type: o.org_type || '',
                  roles_open: fromArray(o.roles_open),
                  project_links: fromArray(o.project_links),
                  email: o.email || '',
                  beta_info: o.beta_info || '',
                  resume_request: !!o.resume_request,
                }}
                onCancel={() => setEditingId(null)}
                onSave={(data) => update(o.id, data)}
              />
            ) : (
              <OrgCard
                key={o.id}
                org={o}
                isMine={!!me && o.owner_id === me.id}
                onEdit={() => setEditingId(o.id)}
                onDelete={() => remove(o.id)}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}
