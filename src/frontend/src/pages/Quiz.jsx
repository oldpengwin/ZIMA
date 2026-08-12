import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../lib/auth.jsx';
import { useNeurotypes } from '../lib/neurotypes.js';
import SectionFlag from '../components/SectionFlag.jsx';
import NeurotypeBadge from '../components/NeurotypeBadge.jsx';
import { PageLoader, Spinner } from '../components/Loader.jsx';

export default function Quiz() {
  const { profile, refresh } = useAuth();
  const reg = useNeurotypes();
  const navigate = useNavigate();
  const [bank, setBank] = useState(null);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getQuiz().then(setBank).catch((e) => setError(e.message));
  }, []);

  if (error && !bank) return <div className="section"><div className="notice error">{error}</div></div>;
  if (!bank) return <div className="section"><PageLoader label="Loading the typology…" /></div>;

  const questions = bank.questions;
  const total = questions.length;
  const q = questions[i];

  const submit = async (finalAnswers) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitQuiz({ answers: finalAnswers });
      setResult(res.result);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const choose = (optionId) => {
    const next = { ...answers, [q.id]: optionId };
    setAnswers(next);
    if (i + 1 < total) setI(i + 1);
    else submit(next);
  };

  const pickIdentified = async (neurotype) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.setIdentified(profile.id, neurotype);
      await refresh();
      navigate('/me');
    } catch (e) {
      setError(e.message);
      setSubmitting(false);
    }
  };

  // ── result + self-select ──
  if (result) {
    return (
      <div className="section" style={{ maxWidth: 660 }}>
        <SectionFlag n={2}>THE TYPOLOGY</SectionFlag>
        <p className="script" style={{ fontSize: '1.6rem', margin: 0 }}>our read on you,</p>
        <h2 className="display h2" style={{ margin: '4px 0 14px' }}>
          {reg?.neurotypes?.[result.top]?.label?.toUpperCase() || result.top}
        </h2>
        <div className="row"><NeurotypeBadge type={result.top} kind="assessed" /></div>
        <p className="muted" style={{ maxWidth: 520 }}>{reg?.neurotypes?.[result.top]?.tagline}</p>

        <hr className="divider" />
        <div className="label" style={{ marginBottom: 12 }}>Your closest archetypes</div>
        <div className="stack" style={{ gap: 10 }}>
          {result.ranked.slice(0, 5).map((r) => (
            <div key={r.id} className="row" style={{ gap: 12 }}>
              <div style={{ width: 150 }}><NeurotypeBadge type={r.id} /></div>
              <div style={{ flex: 1, height: 8, background: 'var(--charcoal)', borderRadius: 999, overflow: 'hidden' }}>
                <div style={{ width: `${r.percentage}%`, height: '100%', background: reg?.neurotypes?.[r.id]?.color?.base || 'var(--cyan)' }} />
              </div>
              <span className="muted" style={{ width: 42, textAlign: 'right' }}>{Math.round(r.percentage)}%</span>
            </div>
          ))}
        </div>

        <hr className="divider" />
        <div className="label" style={{ marginBottom: 4 }}>Now — which do you identify as?</div>
        <p className="hint" style={{ marginTop: 0, marginBottom: 14 }}>
          Two badges: our assessment, and the one you choose. Pick yours.
        </p>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(155px, 1fr))', gap: 8 }}>
          {(reg?.order || []).map((id) => (
            <button
              key={id}
              type="button"
              className="btn btn-ghost"
              onClick={() => pickIdentified(id)}
              disabled={submitting}
              style={{ justifyContent: 'flex-start' }}
            >
              <NeurotypeBadge type={id} />
            </button>
          ))}
        </div>
        {error && <div className="notice error" style={{ marginTop: 14 }}>{error}</div>}
      </div>
    );
  }

  // ── question stepper ──
  return (
    <div className="section" style={{ maxWidth: 640 }}>
      <SectionFlag n={2}>THE TYPOLOGY</SectionFlag>
      <div className="spread" style={{ marginTop: 6, marginBottom: 10 }}>
        <span className="label">Question {i + 1} / {total}</span>
        {i > 0 && !submitting && (
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => setI(i - 1)}>Back</button>
        )}
      </div>
      <div style={{ height: 6, background: 'var(--charcoal)', borderRadius: 999, overflow: 'hidden', marginBottom: 26 }}>
        <div style={{ width: `${(i / total) * 100}%`, height: '100%', background: 'var(--lime)', transition: 'width .3s var(--ease)' }} />
      </div>

      <h3 style={{ fontSize: '1.4rem', fontWeight: 600, lineHeight: 1.3, margin: '0 0 22px' }}>{q.prompt}</h3>

      {submitting ? (
        <Spinner label="Scoring your answers…" />
      ) : (
        <div className="stack">
          {q.options.map((o) => (
            <button
              key={o.id}
              type="button"
              className="card hoverable"
              style={{ textAlign: 'left', cursor: 'pointer', fontSize: '0.98rem' }}
              onClick={() => choose(o.id)}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
      {error && <div className="notice error" style={{ marginTop: 14 }}>{error}</div>}
    </div>
  );
}
