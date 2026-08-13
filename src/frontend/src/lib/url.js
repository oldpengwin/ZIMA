// Only http(s) links may be rendered as an href. Anything else — javascript:,
// data:, vbscript:, or malformed — is dropped, so a link stored via the API
// can't become a clickable XSS vector on a profile.
export function isSafeHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

export function safeLinks(links) {
  return (links || []).filter(isSafeHttpUrl);
}
