import { NavLink } from 'react-router-dom';
import { useAuth } from '../lib/auth.jsx';

const LINKS = [
  { to: '/discover', label: 'Discover' },
  { to: '/network', label: 'Network' },
  { to: '/projects', label: 'Projects' },
  { to: '/organizations', label: 'Organizations' },
  { to: '/matches', label: 'Matches' },
  { to: '/me', label: 'Profile' },
];

export default function Shell({ children }) {
  const { isAuthed, logout } = useAuth();
  return (
    <div className="shell">
      <header className="nav">
        <div className="container nav-inner">
          <NavLink to={isAuthed ? '/discover' : '/'} className="brand">
            ZIMA<span className="dot">.</span>
          </NavLink>
          {isAuthed && (
            <nav className="nav-links">
              {LINKS.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                >
                  {l.label}
                </NavLink>
              ))}
              <button
                type="button"
                className="nav-link"
                onClick={logout}
                style={{ background: 'none', border: 0, cursor: 'pointer' }}
              >
                Log out
              </button>
            </nav>
          )}
        </div>
      </header>

      <main className="container" style={{ flex: 1, width: '100%' }}>{children}</main>

      <footer className="footer">
        <div className="container spread" style={{ width: '100%' }}>
          <span className="watermark">HOPAMINE ›</span>
          <span className="muted" style={{ fontSize: '0.75rem', letterSpacing: '0.04em' }}>
            the builders network · powered by Zima
          </span>
          <div className="dots" aria-hidden="true"><i /><i /><i /></div>
        </div>
      </footer>
    </div>
  );
}
