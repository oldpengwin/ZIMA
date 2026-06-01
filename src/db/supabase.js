import { createClient } from '@supabase/supabase-js';
import { config } from '../config.js';

export const supabase = createClient(config.supabaseUrl, config.supabaseServiceKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

export async function getProfileByDiscordId(discordId) {
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('discord_id', discordId)
    .maybeSingle();

  if (error) throw error;
  return data;
}

export async function upsertProfile(profile) {
  const now = new Date().toISOString();
  const row = {
    ...profile,
    updated_at: now,
  };

  const { data, error } = await supabase
    .from('profiles')
    .upsert(row, { onConflict: 'discord_id' })
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function recordRoleGrant({ discordId, roleKey, source = 'system', metadata = {} }) {
  const { error } = await supabase.from('role_grants').upsert(
    {
      discord_id: discordId,
      role_key: roleKey,
      source,
      metadata,
      granted_at: new Date().toISOString(),
    },
    { onConflict: 'discord_id,role_key' },
  );

  if (error) throw error;
}
