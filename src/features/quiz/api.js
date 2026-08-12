// The quiz API calls now live in the shared bot API client (src/lib/apiClient.js)
// alongside the profile/role calls, so there's one place that talks to the
// Python API. Re-exported here so existing imports keep working.
export { getQuiz, getNeurotypes, submitQuiz, setIdentified } from '../../lib/apiClient.js';
