import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { useNeurotypes } from '../lib/neurotypes.js';
import SectionFlag from '../components/SectionFlag.jsx';
import { PageLoader } from '../components/Loader.jsx';

export default function Network() {
  const reg = useNeurotypes();
  const [net, setNet] = useState(null);
  const [error, setError] = useState(null);
  const [active, setActive] = useState(null);

  useEffect(() => {
    api.getNetwork().then(setNet).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="section"><div className="notice error">{error}</div></div>;
  if (!net || !reg) return <div className="section"><PageLoader label="Loading the network…" /></div>;

  const order = reg.order || net.nodes.map((n) => n.id);
  const counts = Object.fromEntries(net.nodes.map((n) => [n.id, n.count]));
  const maxCount = Math.max(1, ...net.nodes.map((n) => n.count));
  const cx = 260;
  const cy = 260;
  const R = 190;
  const pos = {};
  order.forEach((id, idx) => {
    const a = (idx / order.length) * Math.PI * 2 - Math.PI / 2;
    pos[id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
  });

  const activeCount = net.nodes.filter((n) => n.count > 0).length;

  return (
    <div className="section">
      <SectionFlag n={7}>THE NETWORK</SectionFlag>
      <div className="spread" style={{ margin: '8px 0 2px' }}>
        <h2 className="display h2" style={{ margin: 0 }}>ARCHETYPE MAP</h2>
        <span className="stat">{net.total_builders}</span>
      </div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 18 }}>
        builders across {activeCount} archetype{activeCount === 1 ? '' : 's'}. Tap a node to filter.
      </p>

      <div className="card" style={{ overflow: 'hidden', marginBottom: 20 }}>
        <svg
          viewBox="0 0 520 520"
          style={{ width: '100%', height: 'auto', maxWidth: 560, margin: '0 auto', display: 'block' }}
          role="img"
          aria-label="Archetype network graph"
        >
          {net.edges.map((e, k) =>
            pos[e.source] && pos[e.target] ? (
              <line key={k} x1={pos[e.source].x} y1={pos[e.source].y} x2={pos[e.target].x} y2={pos[e.target].y} stroke="#2c4a5a" strokeWidth={1.4} />
            ) : null,
          )}
          {order.map((id) => {
            const meta = reg.neurotypes[id];
            if (!meta || !pos[id]) return null;
            const c = counts[id] || 0;
            const r = 14 + 22 * Math.sqrt(c / maxCount);
            const isActive = active === id;
            return (
              <g key={id} style={{ cursor: 'pointer' }} onClick={() => setActive(isActive ? null : id)}>
                <circle
                  cx={pos[id].x}
                  cy={pos[id].y}
                  r={r}
                  fill={meta.color.base}
                  stroke={isActive ? '#fff' : meta.color.border}
                  strokeWidth={isActive ? 3 : 2}
                  fillOpacity={active && !isActive ? 0.4 : 0.92}
                />
                <text x={pos[id].x} y={pos[id].y + 5} textAnchor="middle" fontSize="16">{meta.emoji}</text>
                <text x={pos[id].x} y={pos[id].y + r + 14} textAnchor="middle" fontSize="10" fill="#dfeee6" fontWeight="600">
                  {meta.label} · {c}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="label" style={{ marginBottom: 10 }}>
        {active ? `${reg.neurotypes[active]?.label} builders` : 'Recent builders'}
      </div>
      {net.location_points.length === 0 ? (
        <div className="empty">No builders on the map yet — take the typology to be the first.</div>
      ) : (
        <div className="grid cards">
          {net.location_points
            .filter((p) => !active || p.neurotype === active)
            .slice(0, 24)
            .map((p, k) => {
              const meta = reg.neurotypes[p.neurotype];
              return (
                <div key={k} className="card">
                  <strong>{p.display_name}</strong>
                  <div className="row" style={{ gap: 8, marginTop: 8 }}>
                    <span
                      className="badge"
                      style={{ borderColor: meta?.color.border, color: meta?.color.text || meta?.color.border, background: meta?.color.badge_bg }}
                    >
                      <span aria-hidden="true">{meta?.emoji}</span>
                      {meta?.label || p.neurotype}
                    </span>
                    {p.location && <span className="muted" style={{ fontSize: '0.82rem' }}>{p.location}</span>}
                  </div>
                </div>
              );
            })}
        </div>
      )}

      <p className="hint" style={{ marginTop: 16 }}>
        Updated {new Date(net.generated_at).toLocaleTimeString()} · cached ~{Math.round((net.cache_ttl_seconds || 300) / 60)} min
        server-side. A full globe view lives at <code>demo/zima-network-live.html</code>.
      </p>
    </div>
  );
}
