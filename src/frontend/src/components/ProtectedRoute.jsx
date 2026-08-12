import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/auth.jsx';
import { PageLoader } from './Loader.jsx';

// Gate: must be logged in; and (by default) must have a profile, else send to
// onboarding. Waits for the initial auth check so we don't flash the login page.
export default function ProtectedRoute({ children, requireProfile = true }) {
  const { isAuthed, hasProfile, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!isAuthed) return <Navigate to="/" replace />;
  if (requireProfile && !hasProfile) return <Navigate to="/onboarding" replace />;
  return children;
}
