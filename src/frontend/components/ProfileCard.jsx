"""
Profile Card Component - HOPAMINE Brand Compliant

Interactive profile card with proper brand styling and neurotype colors
"""

import React from 'react';
import PropTypes from 'prop-types';

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

const NEUROTYPE_CONFIG = {
  seedcaster: {
    label: 'Seedcaster',
    emoji: '🌱',
    color: BRAND_COLORS.LIME,
    description: 'They plant what others haven’t imagined yet'
  },
  fabricant: {
    label: 'Fabricant',
    emoji: '⚙️',
    color: BRAND_COLORS.DEEP_OCEAN,
    description: 'If it doesn’t exist, they build it'
  },
  mycelian: {
    label: 'Mycelian',
    emoji: '🍄',
    color: BRAND_COLORS.SKY_BLUE,
    description: 'They think in networks and grow in the dark'
  },
  terraformer: {
    label: 'Terraformer',
    emoji: '🏗️',
    color: BRAND_COLORS.LIME,
    description: 'They redesign the spaces we inhabit'
  },
  developer: {
    label: 'Developer',
    emoji: '💻',
    color: BRAND_COLORS.SKY_BLUE,
    description: 'They write the tools of sovereignty'
  },
  artisan: {
    label: 'Artisan',
    emoji: '🎨',
    color: BRAND_COLORS.HOT_MAGENTA,
    description: 'They make the future beautiful enough to want'
  },
  chronicler: {
    label: 'Chronicler',
    emoji: '📡',
    color: BRAND_COLORS.HOT_MAGENTA,
    description: 'They make sure the work gets seen'
  },
  cultivar: {
    label: 'Cultivar',
    emoji: '🌿',
    color: BRAND_COLORS.LIME,
    description: 'They bridge the lab and the land'
  },
  loomkeeper: {
    label: 'Loomkeeper',
    emoji: '🔗',
    color: BRAND_COLORS.HOT_MAGENTA,
    description: 'They hold the network together'
  },
  verdant: {
    label: 'Verdant',
    emoji: '📜',
    color: BRAND_COLORS.DEEP_OCEAN,
    description: 'They change the rules of the game'
  }
};

const ProfileCard = ({ profile, onConnect, showMatchScore }) => {
  const neurotypeConfig = NEUROTYPE_CONFIG[profile.neurotype] || NEUROTYPE_CONFIG.seedcaster;

  return (
    <div className="profile-card" style={{
      backgroundColor: BRAND_COLORS.NEAR_BLACK,
      border: `2px solid ${neurotypeConfig.color}`,
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '20px',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'pointer'
    }}
      onClick={() => onConnect(profile)}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = `0 8px 24px rgba(87, 184, 220, 0.2)`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}>

      {/* Neurotype Badge - HOPAMINE style */}
      <div className="neurotype-badge" style={{
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

      {/* Profile Header - HOPAMINE ALL CAPS style */}
      <div className="profile-header" style={{ marginBottom: '12px' }}>
        <h3 style={{
          fontFamily: '"Geist", -apple-system, sans-serif',
          fontSize: '20px',
          fontWeight: '600',
          color: BRAND_COLORS.OFF_WHITE,
          margin: '0',
          letterSpacing: '-0.5px'
        }}>
          {profile.display_name}
        </h3>
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
      <div className="profile-bio" style={{
        color: BRAND_COLORS.BONE,
        fontSize: '14px',
        lineHeight: '1.5',
        marginBottom: '16px'
      }}>
        {profile.bio}
      </div>

      {/* Skills and Match Score */}
      <div className="profile-meta" style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        marginBottom: '16px'
      }}>
        {profile.skills && profile.skills.slice(0, 4).map((skill, index) => (
          <span key={index} style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '10px',
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

      {/* Match Score - HOPAMINE style */}
      {showMatchScore && (
        <div className="match-score" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: '12px',
          borderTop: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`
        }}>
          <span style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '11px',
            color: BRAND_COLORS.BONE,
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            MATCH SCORE
          </span>
          <span style={{
            fontFamily: '"Geist", -apple-system, sans-serif',
            fontSize: '18px',
            fontWeight: '600',
            color: neurotypeConfig.color
          }}>
            {profile.match_score ? `${Math.round(profile.match_score * 100)}%` : 'N/A'}
          </span>
        </div>
      )}

      {/* Connect Button - HOPAMINE accent color */}
      <button className="connect-button"
        onClick={(e) => {
          e.stopPropagation();
          onConnect(profile);
        }}
        style={{
          width: '100%',
          backgroundColor: neurotypeConfig.color,
          color: BRAND_COLORS.NEAR_BLACK,
          border: 'none',
          padding: '12px',
          borderRadius: '8px',
          fontFamily: '"DM Mono", monospace',
          fontSize: '12px',
          fontWeight: '600',
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
          cursor: 'pointer',
          transition: 'all 0.2s',
          marginTop: '12px'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.02)';
          e.currentTarget.style.boxShadow = `0 4px 12px ${neurotypeConfig.color}40`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = 'none';
        }}>
        CONNECT {neurotypeConfig.emoji}
      </button>
    </div>
  );
};

ProfileCard.propTypes = {
  profile: PropTypes.shape({
    id: PropTypes.string.isRequired,
    display_name: PropTypes.string.isRequired,
    neurotype: PropTypes.oneOf(Object.keys(NEUROTYPE_CONFIG)).isRequired,
    location: PropTypes.string,
    bio: PropTypes.string,
    skills: PropTypes.arrayOf(PropTypes.string),
    match_score: PropTypes.number
  }).isRequired,
  onConnect: PropTypes.func.isRequired,
  showMatchScore: PropTypes.bool
};

ProfileCard.defaultProps = {
  showMatchScore: false
};

export default ProfileCard;