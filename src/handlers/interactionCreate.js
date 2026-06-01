import { CUSTOM_IDS } from '../features/onboarding/constants.js';
import { handleProfileModal, handleStartButton } from '../features/onboarding/flow.js';

export async function onInteractionCreate(interaction) {
  if (interaction.isButton() && interaction.customId === CUSTOM_IDS.START_BUTTON) {
    return handleStartButton(interaction);
  }

  if (interaction.isModalSubmit() && interaction.customId === CUSTOM_IDS.PROFILE_MODAL) {
    return handleProfileModal(interaction);
  }
}
