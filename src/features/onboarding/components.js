import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  EmbedBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
} from 'discord.js';
import { CUSTOM_IDS } from './constants.js';

export function buildWelcomeEmbed() {
  return new EmbedBuilder()
    .setColor(0x5865f2)
    .setTitle('Welcome to the server')
    .setDescription(
      [
        '**Zima** will get you set up in a few steps.',
        '',
        'You will share a short profile (name, location, skills, and more).',
        'Once complete, you receive the **Vetted** role and your info is saved securely.',
        '',
        'Click **Get started** below when you are ready.',
      ].join('\n'),
    )
    .setFooter({ text: 'Zima onboarding' });
}

export function buildStartRow() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(CUSTOM_IDS.START_BUTTON)
      .setLabel('Get started')
      .setStyle(ButtonStyle.Primary),
  );
}

export function buildProfileModal() {
  return new ModalBuilder()
    .setCustomId(CUSTOM_IDS.PROFILE_MODAL)
    .setTitle('Your profile')
    .addComponents(
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(CUSTOM_IDS.FIELD_DISPLAY_NAME)
          .setLabel('Full name')
          .setStyle(TextInputStyle.Short)
          .setRequired(true)
          .setMaxLength(100),
      ),
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(CUSTOM_IDS.FIELD_LOCATION)
          .setLabel('Location (city / region)')
          .setStyle(TextInputStyle.Short)
          .setRequired(true)
          .setMaxLength(100),
      ),
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(CUSTOM_IDS.FIELD_SKILLS)
          .setLabel('Skills (comma-separated)')
          .setStyle(TextInputStyle.Paragraph)
          .setRequired(true)
          .setMaxLength(500)
          .setPlaceholder('e.g. design, video editing, community management'),
      ),
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(CUSTOM_IDS.FIELD_BIO)
          .setLabel('About you')
          .setStyle(TextInputStyle.Paragraph)
          .setRequired(false)
          .setMaxLength(1000),
      ),
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(CUSTOM_IDS.FIELD_LINKS)
          .setLabel('Links (portfolio, socials)')
          .setStyle(TextInputStyle.Short)
          .setRequired(false)
          .setMaxLength(200),
      ),
    );
}

export function parseSkills(raw) {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function getModalField(modalSubmission, customId) {
  return modalSubmission.fields.getTextInputValue(customId);
}
