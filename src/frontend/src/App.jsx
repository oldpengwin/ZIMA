import { Navigate, Route, Routes } from 'react-router-dom';
import Shell from './components/Shell.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Landing from './pages/Landing.jsx';
import AuthCallback from './pages/AuthCallback.jsx';
import Onboarding from './pages/Onboarding.jsx';
import Quiz from './pages/Quiz.jsx';
import Discover from './pages/Discover.jsx';
import ProfileMe from './pages/ProfileMe.jsx';
import ProfileView from './pages/ProfileView.jsx';
import Matches from './pages/Matches.jsx';
import Network from './pages/Network.jsx';

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route
          path="/onboarding"
          element={<ProtectedRoute requireProfile={false}><Onboarding /></ProtectedRoute>}
        />
        <Route path="/quiz" element={<ProtectedRoute><Quiz /></ProtectedRoute>} />
        <Route path="/discover" element={<ProtectedRoute><Discover /></ProtectedRoute>} />
        <Route path="/me" element={<ProtectedRoute><ProfileMe /></ProtectedRoute>} />
        <Route path="/p/:id" element={<ProtectedRoute><ProfileView /></ProtectedRoute>} />
        <Route path="/matches" element={<ProtectedRoute><Matches /></ProtectedRoute>} />
        <Route path="/network" element={<ProtectedRoute><Network /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
