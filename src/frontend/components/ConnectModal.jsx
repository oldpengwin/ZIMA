"""
Connect Modal Component - HOPAMINE Brand Compliant

Interactive connection modal with message templates based on base44 design patterns
"""

import React, { useState, useMemo } from 'react';
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

// Message templates based on base44 patterns
const MESSAGE_TEMPLATES = [
  {
    id: 'collaboration',
    title: 'COLLABORATION REQUEST',
    description: 'Propose working together on a specific project or idea',
    fields: [
      { key: 'project', label: 'PROJECT NAME', placeholder: 'e.g., Urban Farming Network' },
      { key: 'role', label: 'YOUR ROLE', placeholder: 'e.g., Developer, Researcher' },
      { key: 'contribution', label: 'WHAT YOU BRING', placeholder: 'e.g., Software architecture, 10 hrs/week' }
    ],
    buildMessage: (values) =>
      `Hey! I'd love to collaborate on ${values.project || 'a project'}. ` +
      `As a ${values.role || 'contributor'}, I can bring ${values.contribution || 'my skills'}. ` +
      `Let's connect and explore how we can work together!`
  },
  {
    id: 'skill-exchange',
    title: 'SKILL EXCHANGE',
    description: 'Offer your skills in exchange for theirs',
    fields: [
      { key: 'offer', label: 'YOU OFFER', placeholder: 'e.g., Web development, 5 hours' },
      { key: 'request', label: 'YOU REQUEST', placeholder: 'e.g., Graphic design, 3 hours' }
    ],
    buildMessage: (values) =>
      `Skill exchange proposal: I can offer ${values.offer || 'my skills'} ` +
      `in exchange for ${values.request || 'your expertise'}. ` +
      `Would you be open to a skill trade?`
  },
  {
    id: 'introduction',
    title: 'SIMPLE INTRODUCTION',
    description: 'Just say hello and express interest',
    fields: [],
    buildMessage: () =>
      `Hi! I came across your profile and found your work interesting. ` +
      `I'd love to connect and learn more about what you're building.`
  },
  {
    id: 'project-invite',
    title: 'PROJECT INVITATION',
    description: 'Invite them to join your project',
    fields: [
      { key: 'project', label: 'PROJECT NAME', placeholder: 'e.g., Regenerative Tech Collective' },
      { key: 'role', label: 'DESIRED ROLE', placeholder: 'e.g., Community Organizer, Developer' },
      { key: 'commitment', label: 'TIME COMMITMENT', placeholder: 'e.g., 2-5 hours/week' }
    ],
    buildMessage: (values) =>
      `Invitation: Would you be interested in joining ${values.project || 'my project'} ` +
      `as a ${values.role || 'contributor'}? The commitment would be ` +
      `${values.commitment || 'flexible'}. Let me know if you'd like to discuss!`
  }
];

const ConnectModal = ({ targetProfile, onClose, onSend }) => {
  const [templateIdx, setTemplateIdx] = useState(0);
  const [fieldValues, setFieldValues] = useState({});
  const [customMessage, setCustomMessage] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [channel, setChannel] = useState('in_app');

  const template = MESSAGE_TEMPLATES[templateIdx];

  const builtMessage = useMemo(() => {
    if (useCustom) return customMessage;
    return template.buildMessage(fieldValues);
  }, [useCustom, customMessage, template, fieldValues]);

  const handleFieldChange = (key, value) => {
    setFieldValues(prev => ({ ...prev, [key]: value }));
  };

  const handleSend = () => {
    if (!builtMessage.trim()) return;

    onSend({
      to: targetProfile,
      message: builtMessage,
      template: template.id,
      channel
    });

    onClose();
  };

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(19, 19, 19, 0.8)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="modal-content" style={{
        backgroundColor: BRAND_COLORS.NEAR_BLACK,
        border: `2px solid ${BRAND_COLORS.SKY_BLUE}`,
        borderRadius: '16px',
        width: '90%',
        maxWidth: '600px',
        maxHeight: '80vh',
        overflowY: 'auto',
        padding: '0',
        position: 'relative'
      }}>
        {/* Modal Header - HOPAMINE style */}
        <div className="modal-header" style={{
          backgroundColor: BRAND_COLORS.DEEP_OCEAN,
          padding: '16px 24px',
          borderBottom: `1px solid ${BRAND_COLORS.SKY_BLUE}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h3 style={{
            fontFamily: '"Geist", -apple-system, sans-serif',
            fontSize: '18px',
            fontWeight: '600',
            color: BRAND_COLORS.OFF_WHITE,
            margin: '0',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            CONNECT WITH {targetProfile.display_name}
          </h3>
          <button onClick={onClose} style={{
            background: 'none',
            border: 'none',
            color: BRAND_COLORS.OFF_WHITE,
            fontSize: '24px',
            cursor: 'pointer',
            padding: '4px'
          }}>
            ×
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ padding: '24px' }}>
          {/* Template Selector */}
          <div className="template-selector" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', marginBottom: '16px' }}>
              {MESSAGE_TEMPLATES.map((temp, idx) => (
                <button
                  key={temp.id}
                  onClick={() => {
                    setTemplateIdx(idx);
                    setUseCustom(false);
                  }}
                  style={{
                    flex: '0 0 auto',
                    padding: '8px 16px',
                    backgroundColor: idx === templateIdx ? BRAND_COLORS.SKY_BLUE : 'transparent',
                    color: idx === templateIdx ? BRAND_COLORS.NEAR_BLACK : BRAND_COLORS.BONE,
                    border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                    borderRadius: '6px',
                    fontFamily: '"DM Mono", monospace',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {temp.title}
                </button>
              ))}
            </div>

            <p style={{
              fontFamily: '"Geist", -apple-system, sans-serif',
              fontSize: '14px',
              color: BRAND_COLORS.BONE,
              margin: '0',
              lineHeight: '1.4'
            }}>
              {template.description}
            </p>
          </div>

          {/* Message Builder */}
          <div className="message-builder" style={{ marginBottom: '24px' }}>
            {!useCustom ? (
              <div className="template-fields">
                {template.fields.map((field) => (
                  <div key={field.key} style={{ marginBottom: '16px' }}>
                    <label style={{
                      display: 'block',
                      fontFamily: '"DM Mono", monospace',
                      fontSize: '10px',
                      color: BRAND_COLORS.HOT_MAGENTA,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      marginBottom: '4px'
                    }}>
                      {field.label}
                    </label>
                    <input
                      type="text"
                      placeholder={field.placeholder}
                      value={fieldValues[field.key] || ''}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        backgroundColor: 'rgba(87, 184, 220, 0.05)',
                        border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                        borderRadius: '6px',
                        color: BRAND_COLORS.OFF_WHITE,
                        fontFamily: '"Geist", -apple-system, sans-serif',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="custom-message">
                <textarea
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  placeholder="Write your custom message..."
                  style={{
                    width: '100%',
                    minHeight: '120px',
                    padding: '12px',
                    backgroundColor: 'rgba(87, 184, 220, 0.05)',
                    border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                    borderRadius: '6px',
                    color: BRAND_COLORS.OFF_WHITE,
                    fontFamily: '"Geist", -apple-system, sans-serif',
                    fontSize: '14px',
                    resize: 'vertical'
                  }}
                />
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <button
                onClick={() => setUseCustom(!useCustom)}
                style={{
                  flex: 1,
                  padding: '8px',
                  backgroundColor: useCustom ? BRAND_COLORS.SKY_BLUE : 'transparent',
                  color: useCustom ? BRAND_COLORS.NEAR_BLACK : BRAND_COLORS.BONE,
                  border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                  borderRadius: '6px',
                  fontFamily: '"DM Mono", monospace',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  cursor: 'pointer'
                }}
              >
                {useCustom ? 'USE TEMPLATE' : 'CUSTOM MESSAGE'}
              </button>
            </div>
          </div>

          {/* Preview */}
          <div className="message-preview" style={{
            backgroundColor: 'rgba(30, 97, 147, 0.2)',
            border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px'
          }}>
            <p style={{
              fontFamily: '"Geist", -apple-system, sans-serif',
              fontSize: '14px',
              color: BRAND_COLORS.OFF_WHITE,
              lineHeight: '1.5',
              margin: '0',
              whiteSpace: 'pre-wrap'
            }}>
              {builtMessage || 'Your message will appear here...'}
            </p>
          </div>

          {/* Channel Selector */}
          <div className="channel-selector" style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              fontFamily: '"DM Mono", monospace',
              fontSize: '10px',
              color: BRAND_COLORS.HOT_MAGENTA,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '8px'
            }}>
              DELIVERY CHANNEL
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setChannel('in_app')}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: channel === 'in_app' ? BRAND_COLORS.SKY_BLUE : 'transparent',
                  color: channel === 'in_app' ? BRAND_COLORS.NEAR_BLACK : BRAND_COLORS.BONE,
                  border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                  borderRadius: '6px',
                  fontFamily: '"DM Mono", monospace',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  cursor: 'pointer'
                }}
              >
                IN-APP MESSAGE
              </button>
              <button
                onClick={() => setChannel('email')}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: channel === 'email' ? BRAND_COLORS.SKY_BLUE : 'transparent',
                  color: channel === 'email' ? BRAND_COLORS.NEAR_BLACK : BRAND_COLORS.BONE,
                  border: `1px solid ${BRAND_COLORS.DEEP_OCEAN}`,
                  borderRadius: '6px',
                  fontFamily: '"DM Mono", monospace',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  cursor: 'pointer'
                }}
              >
                EMAIL
              </button>
            </div>
          </div>
        </div>

        {/* Modal Footer - HOPAMINE style */}
        <div className="modal-footer" style={{
          backgroundColor: BRAND_COLORS.DEEP_OCEAN,
          padding: '16px 24px',
          borderTop: `1px solid ${BRAND_COLORS.SKY_BLUE}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              backgroundColor: 'transparent',
              color: BRAND_COLORS.OFF_WHITE,
              border: `1px solid ${BRAND_COLORS.OFF_WHITE}`,
              borderRadius: '6px',
              fontFamily: '"DM Mono", monospace',
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              cursor: 'pointer'
            }}
          >
            CANCEL
          </button>
          <button
            onClick={handleSend}
            disabled={!builtMessage.trim()}
            style={{
              padding: '10px 20px',
              backgroundColor: builtMessage.trim() ? BRAND_COLORS.HOT_MAGENTA : '#666',
              color: BRAND_COLORS.NEAR_BLACK,
              border: 'none',
              borderRadius: '6px',
              fontFamily: '"DM Mono", monospace',
              fontSize: '11px',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              cursor: builtMessage.trim() ? 'pointer' : 'not-allowed'
            }}
          >
            SEND MESSAGE
          </button>
        </div>
      </div>
    </div>
  );
};

ConnectModal.propTypes = {
  targetProfile: PropTypes.shape({
    id: PropTypes.string.isRequired,
    display_name: PropTypes.string.isRequired,
    neurotype: PropTypes.string.isRequired
  }).isRequired,
  onClose: PropTypes.func.isRequired,
  onSend: PropTypes.func.isRequired
};

export default ConnectModal;