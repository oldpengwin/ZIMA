import { config } from '../config.js';
import { getProfileByDiscordId } from '../lib/apiClient.js';

export async function onGuildMemberAdd(member) {
  if (member.user.bot) return;

  const channel = member.guild.channels.cache.get(config.onboardingChannelId);
  if (!channel?.isTextBased()) {
    console.warn('Onboarding channel not found or not text-based:', config.onboardingChannelId);
    return;
  }

  const existing = await getProfileByDiscordId(member.id);
  if (existing?.onboarding_completed_at) return;

  await channel.send({
    content: `Hey <@${member.id}> — welcome! Use the **Get started** button above to introduce yourself and get vetted.`,
  });
}
