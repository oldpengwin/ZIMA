import { Link } from 'react-router-dom';
import NeurotypeBadge from './NeurotypeBadge.jsx';

export default function ProfileCard({ profile }) {
  const nt = profile.identified_neurotype || profile.neurotype || profile.assessed_neurotype;
  const skills = profile.skills || [];
  return (
    <Link to={`/p/${profile.id}`} className="card hoverable" style={{ display: 'block' }}>
      <div className="spread" style={{ marginBottom: 8 }}>
        <strong style={{ fontSize: '1.05rem' }}>{profile.display_name}</strong>
        {profile.is_open === false && <span className="tag">not looking</span>}
      </div>
      {profile.location && <div className="label" style={{ marginBottom: 10 }}>{profile.location}</div>}
      {nt && (
        <div className="row" style={{ marginBottom: 10 }}>
          <NeurotypeBadge type={nt} />
        </div>
      )}
      {profile.tagline && (
        <p className="muted" style={{ margin: '0 0 10px', fontSize: '0.9rem' }}>{profile.tagline}</p>
      )}
      {skills.length > 0 && (
        <div className="row" style={{ gap: 6 }}>
          {skills.slice(0, 4).map((s) => (
            <span key={s} className="tag">{s}</span>
          ))}
          {skills.length > 4 && <span className="tag">+{skills.length - 4}</span>}
        </div>
      )}
    </Link>
  );
}
