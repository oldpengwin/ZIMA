"""
Main App Component - HOPAMINE Brand Compliant

Integrates profile cards, matching, and connection system with proper brand styling
"""

import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import ProfileCard from './components/ProfileCard';
import ConnectModal from './components/ConnectModal';
import ProfilePage from './ProfilePage';
import { profileApi, matchApi } from './api';

// HOPAMINE Brand Constants
const BRAND_COLORS = {
  SKY_BLUE: '#57B8DC',
  HOT_MAGENTA: '#E93CA7',
  DEEP_OCEAN: '#1E6193',
  LIME: '#A4C24B',
  BONE: '#E7E4DB',
  OFF_WHITE: '#F4F2EB',
  NEAR_BLACK: '#131313'
};

// Mock data - in production this would come from API
const mockProfiles = [
  {
    id: '1',
    discord_id: 'user1',
    display_name: 'Aisha Okafor',
    neurotype: 'researcher',
    location: 'London / Lagos',
    bio: 'AI safety & bioethics researcher building consent frameworks for community data.',
    skills: ['AI Safety', 'Bioethics', 'Community Research', 'Data Governance'],
    offering: ['research frameworks', 'grant writing', 'ethics audits'],
    looking_for: ['developers', 'legal advisors', 'community orgs'],
    projects: ['ConsentKit', 'BioEthics Commons'],
    match_score: 0.87
  },
  {
    id: '2',
    discord_id: 'user2',
    display_name: 'Marcus Chen',
    neurotype: 'developer',
    location: 'Montreal',
    bio: 'Full-stack engineer specializing in green infrastructure dashboards and distributed systems.',
    skills: ['React', 'Python', 'PostgreSQL', 'Distributed Systems'],
    offering: ['engineering', 'system architecture', 'mentorship'],
    looking_for: ['designers', 'climate orgs', 'operators'],
    projects: ['RegenMap', 'CropDAO'],
    match_score: 0.92
  },
  {
    id: '3',
    discord_id: 'user3',
    display_name: 'Elena Rodriguez',
    neurotype: 'artisan',
    location: 'Barcelona',
    bio: 'Solarpunk designer creating beautiful, functional interfaces for regenerative technologies.',
    skills: ['UI/UX Design', 'Visual Design', 'World-building'],
    offering: ['design systems', 'brand identity', 'illustration'],
    looking_for: ['developers', 'storytellers', 'builders'],
    projects: ['Solarpunk Collective', 'Regenerative UI Kit'],
    match_score: 0.78
  },
  {
    id: '4',
    discord_id: 'user4',
    display_name: 'Jamal Williams',
    neurotype: 'fabricant',
    location: 'Detroit',
    bio: 'Mechanical engineer building open-source hardware for urban farming.',
    skills: ['Mechanical Engineering', 'Fabrication', 'CAD/CAM'],
    offering: ['prototyping', 'hardware design', 'workshop facilitation'],
    looking_for: ['agricultural experts', 'community orgs'],
    projects: ['Urban Farm Hardware', 'Open Ag Tech'],
    match_score: 0.85
  }
];

const App = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load profiles from API
  useEffect(() => {
    const loadProfiles = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch profiles from API
        const data = await profileApi.getAllProfiles(10, 0);

        // If no profiles found, use mock data for demo
        if (data && data.length > 0) {
          setProfiles(data);
        } else {
          setProfiles(mockProfiles);
        }
      } catch (err) {
        console.error('Failed to load profiles:', err);
        setError('Failed to load profiles. Using demo data.');
        setProfiles(mockProfiles);
      } finally {
        setLoading(false);
      }
    };

    loadProfiles();
  }, []);

  const handleConnect = (profile) => {
    setSelectedProfile(profile);
    setShowConnectModal(true);
  };

  const handleSendMessage = async (messageData) => {
    try {
      console.log('Sending connection request:', messageData);

      // Send connection request via API
      await matchApi.requestConnection(messageData.to.id, messageData.message);

      setShowConnectModal(false);
      // Show success message
      alert(`Connection request sent to ${selectedProfile.display_name}!`);
    } catch (error) {
      console.error('Failed to send connection request:', error);
      alert(`Failed to send message. Please try again.`);
    }
  };

  return (
    <div className="app" style={{
      backgroundColor: BRAND_COLORS.NEAR_BLACK,
      color: BRAND_COLORS.OFF_WHITE,
      minHeight: '100vh',
      padding: '20px',
      fontFamily: '"Geist", -apple-system, sans-serif'
    }}>
      {/* HOPAMINE Header - ALL CAPS style */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '40px',
        paddingBottom: '20px',
        borderBottom: `2px solid ${BRAND_COLORS.SKY_BLUE}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            border: `2px solid ${BRAND_COLORS.SKY_BLUE}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: BRAND_COLORS.SKY_BLUE,
            fontSize: '20px'
          }}>
            ⊹
          </div>
          <div>
            <h1 style={{
              fontSize: '24px',
              fontWeight: '600',
              margin: '0',
              letterSpacing: '-0.5px'
            }}>
              HOPAMINE
            </h1>
            <p style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '11px',
              color: BRAND_COLORS.BONE,
              margin: '0',
              letterSpacing: '0.5px',
              textTransform: 'uppercase'
            }}>
              POWERED BY ZIMA
            </p>
          </div>
        </div>
        <div style={{
          fontFamily: '"DM Mono", monospace',
          fontSize: '10px',
          color: BRAND_COLORS.HOT_MAGENTA,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          THE BUILDERS NETWORK
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Kicker - HOPAMINE style */}
        <div style={{
          marginBottom: '20px',
          fontFamily: '"DM Mono", monospace',
          fontSize: '11px',
          color: BRAND_COLORS.SKY_BLUE,
          textTransform: 'uppercase',
          letterSpacing: '1px'
        }}>
          001 / MATCHING INTERFACE
        </div>

        {/* Display Headline - HOPAMINE ALL CAPS */}
        <h2 style={{
          fontSize: 'clamp(32px, 6vw, 64px)',
          fontWeight: '600',
          lineHeight: '0.95',
          letterSpacing: '-1px',
          margin: '0 0 40px',
          color: BRAND_COLORS.OFF_WHITE
        }}>
          FIND YOUR BUILDERS.
        </h2>

        {/* Script Aside - HOPAMINE whisper */}
        <p style={{
          fontFamily: '"Great Vibes", cursive',
          fontSize: '24px',
          color: BRAND_COLORS.HOT_MAGENTA,
          margin: '0 0 40px',
          fontWeight: '400'
        }}>
          Connect with the ones who move your work forward.
        </p>

        {/* Loading State */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '12px',
              color: BRAND_COLORS.BONE,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              LOADING PROFILES...
            </div>
          </div>
        ) : (
          <div className="profiles-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '24px'
          }}>
            {profiles.map(profile => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                onConnect={handleConnect}
                showMatchScore={true}
              />
            ))}
          </div>
        )}

        {/* Stats - HOPAMINE triads */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '20px',
          marginTop: '60px',
          paddingTop: '40px',
          borderTop: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '36px',
              fontWeight: '600',
              color: BRAND_COLORS.SKY_BLUE,
              marginBottom: '8px'
            }}>
              {profiles.length}+
            </div>
            <div style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.BONE,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              ACTIVE BUILDERS
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '36px',
              fontWeight: '600',
              color: BRAND_COLORS.HOT_MAGENTA,
              marginBottom: '8px'
            }}>
              10
            </div>
            <div style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.BONE,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              NEUROTYPES
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '36px',
              fontWeight: '600',
              color: BRAND_COLORS.LIME,
              marginBottom: '8px'
            }}>
              24
            </div>
            <div style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.BONE,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              OPEN PROJECTS
            </div>
          </div>
        </div>
      </main>

      {/* Footer - HOPAMINE style */}
      <footer style={{
        marginTop: '80px',
        paddingTop: '40px',
        borderTop: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontFamily: '"DM Mono", monospace',
        fontSize: '10px',
        color: BRAND_COLORS.BONE,
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        <div>
          <span style={{ marginRight: '16px' }}>⊹ HOPAMINE</span>
          <span>POWERED BY ZIMA</span>
        </div>
        <div>
          {user && (
            <button
              onClick={onLogout}
              style={{
                background: 'none',
                border: `1px solid ${BRAND_COLORS.HOT_MAGENTA}`,
                color: BRAND_COLORS.HOT_MAGENTA,
                padding: '4px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
                marginRight: '16px'
              }}
            >
              LOGOUT
            </button>
          )}
          <span style={{ marginRight: '16px' }}>DEMO BUILD</span>
          <span>MOCK DATA</span>
        </div>
      </footer>

      {/* Connect Modal */}
      {showConnectModal && selectedProfile && (
        <ConnectModal
          targetProfile={selectedProfile}
          onClose={() => setShowConnectModal(false)}
          onSend={handleSendMessage}
        />
      )}
    </div>
  );
};

const AppWrapper = (props) => {
  return (
    <Routes>
      <Route path="/" element={<App {...props} />} />
      <Route path="/profile/:profileId" element={<ProfilePage />} />
    </Routes>
  );
};

export default AppWrapper;