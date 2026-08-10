import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { profileApi, matchApi } from './api';

const BRAND_COLORS = {
  SKY_BLUE: '#57B8DC',
  HOT_MAGENTA: '#E93CA7',
  DEEP_OCEAN: '#1E6193',
  LIME: '#A4C24B',
  BONE: '#E7E4DB',
  OFF_WHITE: '#F4F2EB',
  NEAR_BLACK: '#131313'
};

const NEUROTYPE_CONFIG = {
  seedcaster: { label: 'Seedcaster', emoji: '🌱', color: BRAND_COLORS.LIME },
  fabricant: { label: 'Fabricant', emoji: '⚙️', color: BRAND_COLORS.DEEP_OCEAN },
  mycelian: { label: 'Mycelian', emoji: '🍄', color: BRAND_COLORS.SKY_BLUE },
  terraformer: { label: 'Terraformer', emoji: '🏗️', color: BRAND_COLORS.LIME },
  developer: { label: 'Developer', emoji: '💻', color: BRAND_COLORS.SKY_BLUE },
  artisan: { label: 'Artisan', emoji: '🎨', color: BRAND_COLORS.HOT_MAGENTA },
  chronicler: { label: 'Chronicler', emoji: '📡', color: BRAND_COLORS.HOT_MAGENTA },
  cultivar: { label: 'Cultivar', emoji: '🌿', color: BRAND_COLORS.LIME },
  loomkeeper: { label: 'Loomkeeper', emoji: '🔗', color: BRAND_COLORS.HOT_MAGENTA },
  verdant: { label: 'Verdant', emoji: '📜', color: BRAND_COLORS.DEEP_OCEAN }
};

const ProfilePage = () => {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load profile
        const profileData = await profileApi.getProfileById(profileId);
        setProfile(profileData);

        // Load matches for this profile
        const matchesData = await matchApi.findMatches(profileId, 3);
        setMatches(matchesData.matches || []);
      } catch (err) {
        console.error('Failed to load profile data:', err);
        setError('Failed to load profile data.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [profileId]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: BRAND_COLORS.BONE }}>
        Loading profile...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: BRAND_COLORS.HOT_MAGENTA }}>
        {error}
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: BRAND_COLORS.BONE }}>
        Profile not found
      </div>
    );
  }

  const neurotypeConfig = NEUROTYPE_CONFIG[profile.neurotype] || NEUROTYPE_CONFIG.developer;

  return (
    <div style={{
      backgroundColor: BRAND_COLORS.NEAR_BLACK,
      color: BRAND_COLORS.OFF_WHITE,
      minHeight: '100vh',
      padding: '20px'
    }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: 'none',
          border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
          color: BRAND_COLORS.BONE,
          padding: '8px 16px',
          borderRadius: '6px',
          marginBottom: '20px',
          cursor: 'pointer'
        }}
      >
        ← BACK
      </button>

      <div style={{
        maxWidth: '800px',
        margin: '0 auto'
      }}>
        {/* Neurotype Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '16px'
        }}>
          <span style={{ fontSize: '24px' }}>{neurotypeConfig.emoji}</span>
          <span style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '12px',
            letterSpacing: '0.5px',
            textTransform: 'uppercase',
            color: neurotypeConfig.color,
            backgroundColor: 'rgba(87, 184, 220, 0.1)',
            padding: '4px 8px',
            borderRadius: '4px'
          }}>
            {neurotypeConfig.label}
          </span>
        </div>

        {/* Profile Header */}
        <div style={{ marginBottom: '12px' }}>
          <h1 style={{
            fontFamily: '"Geist", -apple-system, sans-serif',
            fontSize: '36px',
            fontWeight: '600',
            color: BRAND_COLORS.OFF_WHITE,
            margin: '0',
            letterSpacing: '-0.5px'
          }}>
            {profile.display_name}
          </h1>
          <p style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '11px',
            color: BRAND_COLORS.BONE,
            margin: '4px 0 0',
            letterSpacing: '0.5px',
            textTransform: 'uppercase'
          }}>
            {profile.location || 'GLOBAL'}
          </p>
        </div>

        {/* Profile Bio */}
        <div style={{
          color: BRAND_COLORS.BONE,
          fontSize: '16px',
          lineHeight: '1.6',
          marginBottom: '24px'
        }}>
          {profile.bio}
        </div>

        {/* Skills */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '10px',
            color: BRAND_COLORS.HOT_MAGENTA,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            SKILLS
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {profile.skills && profile.skills.map((skill, index) => (
              <span key={index} style={{
                fontFamily: '"DM Mono", monospace',
                fontSize: '11px',
                color: neurotypeConfig.color,
                backgroundColor: 'rgba(87, 184, 220, 0.1)',
                padding: '4px 8px',
                borderRadius: '4px',
                border: `1px solid ${neurotypeConfig.color}33`
              }}>
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Offering */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '10px',
            color: BRAND_COLORS.HOT_MAGENTA,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            OFFERING
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {profile.offering && profile.offering.map((item, index) => (
              <span key={index} style={{
                fontFamily: '"DM Mono", monospace',
                fontSize: '11px',
                color: BRAND_COLORS.LIME,
                backgroundColor: 'rgba(164, 194, 75, 0.1)',
                padding: '4px 8px',
                borderRadius: '4px',
                border: `1px solid ${BRAND_COLORS.LIME}33`
              }}>
                {item}
              </span>
            ))}
          </div>
        </div>

        {/* Looking For */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '10px',
            color: BRAND_COLORS.HOT_MAGENTA,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            LOOKING FOR
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {profile.looking_for && profile.looking_for.map((item, index) => (
              <span key={index} style={{
                fontFamily: '"DM Mono", monospace',
                fontSize: '11px',
                color: BRAND_COLORS.SKY_BLUE,
                backgroundColor: 'rgba(87, 184, 220, 0.1)',
                padding: '4px 8px',
                borderRadius: '4px',
                border: `1px solid ${BRAND_COLORS.SKY_BLUE}33`
              }}>
                {item}
              </span>
            ))}
          </div>
        </div>

        {/* Projects */}
        {profile.projects && profile.projects.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.HOT_MAGENTA,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '8px'
            }}>
              PROJECTS
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {profile.projects.map((project, index) => (
                <span key={index} style={{
                  fontFamily: '"DM Mono", monospace',
                  fontSize: '11px',
                  color: BRAND_COLORS.DEEP_OCEAN,
                  backgroundColor: 'rgba(30, 97, 147, 0.1)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}33`
                }}>
                  {project}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Top Matches */}
        {matches.length > 0 && (
          <div style={{ marginTop: '40px' }}>
            <h2 style={{
              fontFamily: '"DM Mono", monospace',
              fontSize: '12px',
              color: BRAND_COLORS.HOT_MAGENTA,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '16px'
            }}>
              TOP MATCHES
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
              {matches.map((match, index) => {
                const matchProfile = match.profile;
                const matchNeurotype = NEUROTYPE_CONFIG[matchProfile.neurotype] || NEUROTYPE_CONFIG.developer;
                const score = match.score.total * 100;

                return (
                  <div key={index} style={{
                    backgroundColor: BRAND_COLORS.NEAR_BLACK,
                    border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                    borderRadius: '12px',
                    padding: '16px',
                    cursor: 'pointer'
                  }} onClick={() => navigate(`/profile/${matchProfile.id}`)}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '18px' }}>{matchNeurotype.emoji}</span>
                        <span style={{ fontWeight: '600', fontSize: '16px' }}>{matchProfile.display_name}</span>
                      </div>
                      <span style={{ color: matchNeurotype.color, fontWeight: '600' }}>
                        {Math.round(score)}%
                      </span>
                    </div>
                    <p style={{ color: BRAND_COLORS.BONE, fontSize: '14px', margin: '0' }}>
                      {matchProfile.bio?.substring(0, 100)}{matchProfile.bio?.length > 100 ? '...' : ''}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
