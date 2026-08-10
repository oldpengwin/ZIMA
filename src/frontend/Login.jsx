import React, { useState } from 'react';
import { authApi } from './api';
import { useNavigate } from 'react-router-dom';

const BRAND_COLORS = {
  SKY_BLUE: '#57B8DC',
  HOT_MAGENTA: '#E93CA7',
  DEEP_OCEAN: '#1E6193',
  LIME: '#A4C24B',
  BONE: '#E7E4DB',
  OFF_WHITE: '#F4F2EB',
  NEAR_BLACK: '#131313'
};

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await authApi.login(username, password);

      // Store token
      localStorage.setItem('zima_token', response.access_token);

      // Get user profile
      const user = await authApi.getCurrentUser();

      // Call onLogin callback
      if (onLogin) {
        onLogin(user);
      }

      // Redirect to main app
      navigate('/');
    } catch (err) {
      console.error('Login error:', err);
      setError('Invalid username or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      backgroundColor: BRAND_COLORS.NEAR_BLACK,
      color: BRAND_COLORS.OFF_WHITE,
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: '"Geist", -apple-system, sans-serif'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        backgroundColor: BRAND_COLORS.DEEP_OCEAN,
        border: `2px solid ${BRAND_COLORS.SKY_BLUE}`,
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 8px 32px rgba(87, 184, 220, 0.1)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{
            fontSize: '36px',
            fontWeight: '600',
            letterSpacing: '-1px',
            marginBottom: '8px',
            color: BRAND_COLORS.OFF_WHITE
          }}>
            HOPAMINE
          </div>
          <div style={{
            fontFamily: '"DM Mono", monospace',
            fontSize: '11px',
            color: BRAND_COLORS.BONE,
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            POWERED BY ZIMA
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '24px' }}>
            <label htmlFor="username" style={{
              display: 'block',
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.HOT_MAGENTA,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '8px'
            }}>
              USERNAME
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: 'rgba(87, 184, 220, 0.1)',
                border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                borderRadius: '8px',
                color: BRAND_COLORS.OFF_WHITE,
                fontFamily: '"Geist", -apple-system, sans-serif',
                fontSize: '14px'
              }}
            />
          </div>

          <div style={{ marginBottom: '32px' }}>
            <label htmlFor="password" style={{
              display: 'block',
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.HOT_MAGENTA,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '8px'
            }}>
              PASSWORD
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: 'rgba(87, 184, 220, 0.1)',
                border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                borderRadius: '8px',
                color: BRAND_COLORS.OFF_WHITE,
                fontFamily: '"Geist", -apple-system, sans-serif',
                fontSize: '14px'
              }}
            />
          </div>

          {error && (
            <div style={{
              color: BRAND_COLORS.HOT_MAGENTA,
              backgroundColor: 'rgba(233, 60, 167, 0.1)',
              padding: '12px',
              borderRadius: '8px',
              marginBottom: '24px',
              fontSize: '14px',
              textAlign: 'center'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '16px',
              backgroundColor: loading ? '#666' : BRAND_COLORS.HOT_MAGENTA,
              color: BRAND_COLORS.NEAR_BLACK,
              border: 'none',
              borderRadius: '8px',
              fontFamily: '"DM Mono", monospace',
              fontSize: '12px',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s'
            }}
          >
            {loading ? 'LOGGING IN...' : 'LOGIN'}
          </button>
        </form>

        <div style={{
          marginTop: '32px',
          textAlign: 'center',
          fontFamily: '"DM Mono", monospace',
          fontSize: '10px',
          color: BRAND_COLORS.BONE,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          <div>DEMO BUILD</div>
          <div style={{ marginTop: '4px' }}>USE: mock_user / mock_password</div>
        </div>
      </div>
    </div>
  );
};

export default Login;
