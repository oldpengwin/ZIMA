import { CUSTOM_IDS } from '../features/onboarding/constants.js';
import { handleProfileModal, handleStartButton } from '../features/onboarding/flow.js';
import { QUIZ_IDS } from '../features/quiz/constants.js';
import { handleAnswer, handleIdentify, startQuiz } from '../features/quiz/flow.js';
import { getXp } from '../lib/apiClient.js';
import {
  handleConnect,
  handleMatches,
  handleProfile,
  handleProjects,
} from '../features/social/commands.js';

// ── XP command ── read-only view of the caller's own XP standing. XP is only
// ever awarded server-side off real actions (see services/xp_service.py); this
// just surfaces it. Ephemeral so it doesn't spam the channel.
async function handleXp(interaction) {
  await interaction.deferReply({ ephemeral: true });
  try {
    const s = await getXp(interaction.user.id);
    const lines = [`**Level ${s.level}** — ${s.xp} XP`];
    lines.push(
      s.next_level_at != null
        ? `${s.xp_to_next_level} XP to level ${s.level + 1}.`
        : "You're at the top level. 🎉",
    );
    if (s.unlocked_tiers && s.unlocked_tiers.length) {
      lines.push(`Unlocked tiers: ${s.unlocked_tiers.join(', ')}`);
    }
    await interaction.editReply(lines.join('\n'));
  } catch (err) {
    console.error('/xp failed:', err);
    await interaction.editReply("Couldn't fetch your XP right now — try again in a moment.");
  }
}

export async function onInteractionCreate(interaction) {
  // ── Onboarding ──
  if (interaction.isButton() && interaction.customId === CUSTOM_IDS.START_BUTTON) {
    return handleStartButton(interaction);
  }
  if (interaction.isModalSubmit() && interaction.customId === CUSTOM_IDS.PROFILE_MODAL) {
    return handleProfileModal(interaction);
  }

  // ── Neurotype typology quiz ──
  if (interaction.isChatInputCommand() && interaction.commandName === 'quiz') {
    return startQuiz(interaction);
  }
  if (interaction.isChatInputCommand() && interaction.commandName === 'xp') {
    return handleXp(interaction);
  }
  if (interaction.isChatInputCommand() && interaction.commandName === 'profile') {
    return handleProfile(interaction);
  }
  if (interaction.isChatInputCommand() && interaction.commandName === 'matches') {
    return handleMatches(interaction);
  }
  if (interaction.isChatInputCommand() && interaction.commandName === 'projects') {
    return handleProjects(interaction);
  }
  if (interaction.isChatInputCommand() && interaction.commandName === 'connect') {
    return handleConnect(interaction);
  }
  if (interaction.isButton() && interaction.customId === QUIZ_IDS.START) {
    return startQuiz(interaction);
  }
  if (interaction.isStringSelectMenu() && interaction.customId === QUIZ_IDS.ANSWER) {
    return handleAnswer(interaction);
  }
  if (interaction.isStringSelectMenu() && interaction.customId === QUIZ_IDS.IDENTIFY) {
    return handleIdentify(interaction);
  }
}
