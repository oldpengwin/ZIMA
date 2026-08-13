export function Spinner({ label }) {
  return (
    <span className="row" style={{ gap: 10 }}>
      <span className="spinner" role="status" aria-label={label || 'Loading'} />
      {label && <span className="muted">{label}</span>}
    </span>
  );
}

export function PageLoader({ label = 'Loading…' }) {
  return (
    <div className="empty">
      <Spinner label={label} />
    </div>
  );
}
