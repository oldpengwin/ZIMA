import 'dotenv/config';

function env(...names) {
  for (const name of names) {
    if (process.env[name]) return process.env[name];
  }
  return null;
}

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function requiredOneOf(...names) {
  const value = env(...names);
  if (!value) {
    throw new Error(`Missing required environment variable (one of): ${names.join(', ')}`);
  }
  return value;
}

export const config = {
  discordToken: required('DISCORD_TOKEN'),
  applicationId: requiredOneOf('DISCORD_APPLICATION_ID', 'DISCORD_CLIENT_ID'),
  serverId: env('DISCORD_SERVER_ID', 'DISCORD_GUILD_ID'),
  onboardingChannelId: required('ONBOARDING_CHANNEL_ID'),
  vettedRoleId: required('VETTED_ROLE_ID'),
  // Supabase is no longer required: the bot writes profiles/roles/quiz through
  // the Python API (below), not a direct service-role connection. Kept optional
  // for any future direct use, but the bot boots fine without them.
  supabaseUrl: env('SUPABASE_URL'),
  supabaseServiceKey: env('SUPABASE_SERVICE_ROLE_KEY'),
  // Python API — the bot's real backend now. BOT_API_KEY is required (must match
  // the backend's BOT_API_KEY); without it the bot can't onboard or run the quiz.
  apiBaseUrl: env('API_BASE_URL', 'ZIMA_API_URL') || 'http://localhost:8000',
  botApiKey: required('BOT_API_KEY'),
};

/** Role keys map to Discord role IDs — extend for quest rewards later */
export const roleKeys = {
  vetted: config.vettedRoleId,
};
