import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import SectionFlag from '../components/SectionFlag.jsx';
import { Spinner } from '../components/Loader.jsx';

const STATUSES = ['idea', 'building', 'launched'];
const toArray = (s) => (s || '').split(',').map((x) => x.trim()).filter(Boolean);
const fromArray = (a) => (a || []).join(', ');

const emptyForm = { title: '', description: '', status: 'idea', neurotypes_needed: '', skills_needed: '' };

function ProjectForm({ initial, onCancel, onSave }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) {
      setError('Title is required.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSave({
        title: form.title.trim(),
        description: form.description.trim() || null,
        status: form.status,
        neurotypes_needed: toArray(form.neurotypes_needed),
        skills_needed: toArray(form.skills_needed),
      });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="panel" style={{ marginBottom: 20 }}>
      <div className="field">
        <label htmlFor="pt">Title</label>
        <input id="pt" className="input" value={form.title} onChange={set('title')} maxLength={200} required />
      </div>
      <div className="field">
        <label htmlFor="pd">Description</label>
        <textarea id="pd" className="textarea" value={form.description} onChange={set('description')} maxLength={5000} />
      </div>
      <div className="field">
        <label htmlFor="ps">Status</label>
        <select id="ps" className="input" value={form.status} onChange={set('status')}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="pn">Neurotypes needed (comma-separated)</label>
        <input id="pn" className="input" value={form.neurotypes_needed} onChange={set('neurotypes_needed')} />
      </div>
      <div className="field">
        <label htmlFor="pk">Skills needed (comma-separated)</label>
        <input id="pk" className="input" value={form.skills_needed} onChange={set('skills_needed')} />
      </div>
      {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="row">
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  );
}

function ProjectCard({ project, isMine, onJoin, onEdit, onDelete }) {
  return (
    <div className="card">
      <div className="spread" style={{ marginBottom: 8 }}>
        <strong style={{ fontSize: '1.05rem' }}>{project.title}</strong>
        <span className="tag">{project.status}</span>
      </div>
      {project.owner_deleted && <div className="label" style={{ marginBottom: 8 }}>owner account deleted</div>}
      {project.description && <p className="muted" style={{ margin: '0 0 10px', fontSize: '0.9rem' }}>{project.description}</p>}
      {project.skills_needed?.length > 0 && (
        <div className="row" style={{ gap: 6, marginBottom: 8 }}>
          {project.skills_needed.map((s) => <span key={s} className="tag">{s}</span>)}
        </div>
      )}
      {project.neurotypes_needed?.length > 0 && (
        <div className="row" style={{ gap: 6, marginBottom: 10 }}>
          {project.neurotypes_needed.map((n) => <span key={n} className="tag">{n}</span>)}
        </div>
      )}
      <div className="row" style={{ gap: 8 }}>
        {isMine ? (
          <>
            <button className="btn btn-sm" onClick={onEdit}>Edit</button>
            <button className="btn btn-sm btn-danger" onClick={onDelete}>Delete</button>
          </>
        ) : (
          <button className="btn btn-sm btn-lime" onClick={onJoin}>Join</button>
        )}
      </div>
    </div>
  );
}

export default function Projects() {
  const { profile: me } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = async (status) => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await api.listProjects({ status: status || undefined, limit: 50 }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const create = async (data) => {
    await api.createProject(data);
    setCreating(false);
    setNotice('Project created.');
    await load(statusFilter);
  };

  const update = async (id, data) => {
    await api.updateProject(id, data);
    setEditingId(null);
    setNotice('Project updated.');
    await load(statusFilter);
  };

  const remove = async (id) => {
    try {
      await api.deleteProject(id);
      setNotice('Project deleted.');
      await load(statusFilter);
    } catch (e) {
      setError(e.message);
    }
  };

  const join = async (id) => {
    try {
      await api.joinProject(id);
      setNotice('You joined this project.');
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="section">
      <SectionFlag n={8}>BUILD</SectionFlag>
      <div className="spread" style={{ margin: '8px 0 18px' }}>
        <h2 className="display h2" style={{ margin: 0 }}>PROJECTS</h2>
        {!creating && <button className="btn btn-primary" onClick={() => setCreating(true)}>New project</button>}
      </div>

      {creating && (
        <ProjectForm initial={emptyForm} onCancel={() => setCreating(false)} onSave={create} />
      )}

      <div className="row" style={{ marginBottom: 20, gap: 8 }}>
        <button
          className={`btn btn-sm${statusFilter === '' ? ' btn-lime' : ''}`}
          onClick={() => setStatusFilter('')}
        >
          All
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            className={`btn btn-sm${statusFilter === s ? ' btn-lime' : ''}`}
            onClick={() => setStatusFilter(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {notice && <div className="notice ok" style={{ marginBottom: 16 }}>{notice}</div>}
      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      {loading ? (
        <Spinner label="Loading projects…" />
      ) : projects.length === 0 ? (
        <div className="empty">No projects yet — start one.</div>
      ) : (
        <div className="grid cards">
          {projects.map((p) =>
            editingId === p.id ? (
              <ProjectForm
                key={p.id}
                initial={{
                  title: p.title,
                  description: p.description || '',
                  status: p.status,
                  neurotypes_needed: fromArray(p.neurotypes_needed),
                  skills_needed: fromArray(p.skills_needed),
                }}
                onCancel={() => setEditingId(null)}
                onSave={(data) => update(p.id, data)}
              />
            ) : (
              <ProjectCard
                key={p.id}
                project={p}
                isMine={!!me && p.owner_id === me.id}
                onJoin={() => join(p.id)}
                onEdit={() => setEditingId(p.id)}
                onDelete={() => remove(p.id)}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}
