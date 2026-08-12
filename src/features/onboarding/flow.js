import { MessageFlags } from 'discord.js';
import { getProfileByDiscordId, upsertProfile } from '../../db/supabase.js';
import { grantRole, RoleGrantError } from '../../roles/roleManager.js';
import {
  buildProfileModal,
  buildStartRow,
  buildWelcomeEmbed,
  getModalField,
  parseLinks,
  parseSkills,
} from './components.js';
import { CUSTOM_IDS } from './constants.js';

export async function postOnboardingMessage(channel) {
  const embed = buildWelcomeEmbed();
  const row = buildStartRow();
  return channel.send({ embeds: [embed], components: [row] });
}

export async function handleStartButton(interaction) {
  const existing = await getProfileByDiscordId(interaction.user.id);
  if (existing?.onboarding_completed_at) {
    return interaction.reply({
      content: 'You have already completed onboarding. Contact a moderator if you need to update your profile.',
      flags: MessageFlags.Ephemeral,
    });
  }

  return interaction.showModal(buildProfileModal());
}

export async function handleProfileModal(interaction) {
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  const member = interaction.member;
  if (!member) {
    return interaction.editReply({ content: 'This only works inside a server.' });
  }

  const displayName = getModalField(interaction, CUSTOM_IDS.FIELD_DISPLAY_NAME);
  const location = getModalField(interaction, CUSTOM_IDS.FIELD_LOCATION);
  const skills = parseSkills(getModalField(interaction, CUSTOM_IDS.FIELD_SKILLS));
  const bio = getModalField(interaction, CUSTOM_IDS.FIELD_BIO) || null;
  const links = parseLinks(getModalField(interaction, CUSTOM_IDS.FIELD_LINKS));
  const discordUsername = interaction.user.username;

  try {
    await upsertProfile({
      discord_id: interaction.user.id,
      discord_username: discordUsername,
      display_name: displayName,
      location,
      skills,
      bio,
      links,
      onboarding_completed_at: new Date().toISOString(),
    });

    await grantRole(member, 'vetted', {
      source: 'onboarding',
      metadata: { display_name: displayName },
    });

    return interaction.editReply({
      content: [
        `Thanks, **${displayName}**! Your profile is saved.`,
        `You have been given the **Vetted** role. Welcome aboard.`,
      ].join('\n'),
    });
  } catch (err) {
    console.error('Onboarding failed:', err);

    if (err instanceof RoleGrantError) {
      return interaction.editReply({
        content: [
          `Thanks, **${displayName}**! Your profile is saved.`,
          '',
          `I could not assign the **Vetted** role yet:`,
          err.userMessage,
        ].join('\n'),
      });
    }

    return interaction.editReply({
      content: 'Something went wrong saving your profile. Please try again or ping a moderator.',
    });
  }
}
