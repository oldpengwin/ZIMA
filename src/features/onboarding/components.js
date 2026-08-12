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

// Only http(s) URLs are allowed through. This blocks `javascript:`, `data:`,
// `vbscript:` and other dangerous schemes from ever being stored — they'd
// otherwise become a stored-XSS vector the moment a link is rendered as an
// href on the web frontend.
export function isSafeHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

// Splits the free-text "links" modal field into an array. Accepts
// comma-separated or newline-separated input so the Discord long-text field
// stays a single input for the user. This exists because the canonical
// Postgres schema's `profiles.links` column is text[] (matching the richer
// product data model), so the bot's write path needs to produce an array,
// not the raw scalar string it previously passed through unparsed. Every entry
// is validated as an http(s) URL and the list is capped, so nothing unsafe or
// unbounded reaches the database.
export function parseLinks(raw) {
  if (!raw) return [];
  return raw
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .filter(isSafeHttpUrl)
    .slice(0, 10);
}

export function getModalField(modalSubmission, customId) {
  return modalSubmission.fields.getTextInputValue(customId);
}
