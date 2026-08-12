import { useNeurotypes } from '../lib/neurotypes.js';

// Two-badge system: `kind` is "assessed" (the quiz's read) or "identified"
// (what the person chose). Colours come from the backend registry.
export default function NeurotypeBadge({ type, kind }) {
  const reg = useNeurotypes();
  if (!type) return null;
  const meta = reg?.neurotypes?.[type];
  const color = meta?.color || { base: '#5bcbfa', border: '#3b8189', text: '#0c1410' };

  return (
    <span
      className="badge"
      style={{ background: color.badge_bg || 'transparent', borderColor: color.border, color: color.text || color.border }}
      title={meta?.tagline || type}
    >
      <span className="b-emoji" aria-hidden="true">{meta?.emoji || '◆'}</span>
      <span>{meta?.label || type}</span>
      {kind && <span className="b-kind">{kind}</span>}
    </span>
  );
}
