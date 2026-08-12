// In-memory quiz sessions, keyed by Discord user id. Deliberately not persisted:
// a session is a few minutes of "which question am I on"; if the bot restarts,
// the user just re-runs /quiz. Answers only become durable when submitted to the
// API. Keeps the bot stateless-enough and dependency-free.
//
// A TTL sweep drops abandoned sessions so the Map can't grow unbounded.

const SESSION_TTL_MS = 30 * 60 * 1000; // 30 minutes
const sessions = new Map();

export function startSession(userId, quiz, neurotypes) {
  const session = {
    version: quiz.version,
    questions: quiz.questions,
    neurotypes, // { id: {label, emoji, tagline, ...} }
    answers: {},
    index: 0,
    startedAt: Date.now(),
  };
  sessions.set(userId, session);
  return session;
}

export function getSession(userId) {
  const s = sessions.get(userId);
  if (!s) return null;
  if (Date.now() - s.startedAt > SESSION_TTL_MS) {
    sessions.delete(userId);
    return null;
  }
  return s;
}

export function endSession(userId) {
  sessions.delete(userId);
}

// Periodic sweep of expired sessions.
setInterval(() => {
  const now = Date.now();
  for (const [userId, s] of sessions) {
    if (now - s.startedAt > SESSION_TTL_MS) sessions.delete(userId);
  }
}, SESSION_TTL_MS).unref?.();
