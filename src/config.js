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
  supabaseUrl: required('SUPABASE_URL'),
  supabaseServiceKey: required('SUPABASE_SERVICE_ROLE_KEY'),
  // Python API (neurotype quiz scoring, network). Optional so the bot still
  // boots without them; the quiz feature reports itself unavailable if unset.
  apiBaseUrl: env('API_BASE_URL', 'ZIMA_API_URL') || 'http://localhost:8000',
  botApiKey: env('BOT_API_KEY') || '',
};

/** Role keys map to Discord role IDs — extend for quest rewards later */
export const roleKeys = {
  vetted: config.vettedRoleId,
};
