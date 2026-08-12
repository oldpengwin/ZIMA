import { CUSTOM_IDS } from '../features/onboarding/constants.js';
import { handleProfileModal, handleStartButton } from '../features/onboarding/flow.js';
import { QUIZ_IDS } from '../features/quiz/constants.js';
import { handleAnswer, handleIdentify, startQuiz } from '../features/quiz/flow.js';

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
