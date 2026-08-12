import {
  ActionRowBuilder,
  EmbedBuilder,
  MessageFlags,
  StringSelectMenuBuilder,
} from 'discord.js';
import { QUIZ_IDS } from './constants.js';
import { getNeurotypes, getQuiz, setIdentified, submitQuiz } from './api.js';
import { endSession, getSession, startSession } from './session.js';

const ACCENT = 0x4fb477;

function questionEmbed(session) {
  const q = session.questions[session.index];
  return new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle(`Zima Typology — ${session.index + 1}/${session.questions.length}`)
    .setDescription(q.prompt)
    .setFooter({ text: 'No wrong answers — pick what actually fits.' });
}

function answerRow(session) {
  const q = session.questions[session.index];
  const menu = new StringSelectMenuBuilder()
    .setCustomId(QUIZ_IDS.ANSWER)
    .setPlaceholder('Pick the one that fits best')
    .addOptions(q.options.slice(0, 25).map((o) => ({ label: o.label.slice(0, 100), value: o.id })));
  return new ActionRowBuilder().addComponents(menu);
}

function identifyRow(neurotypes) {
  const menu = new StringSelectMenuBuilder()
    .setCustomId(QUIZ_IDS.IDENTIFY)
    .setPlaceholder('Now pick the one YOU identify as')
    .addOptions(
      Object.values(neurotypes)
        .slice(0, 25)
        .map((n) => ({
          label: `${n.emoji ?? ''} ${n.label}`.trim().slice(0, 100),
          value: n.id,
          description: (n.tagline ?? '').slice(0, 100) || undefined,
        })),
    );
  return new ActionRowBuilder().addComponents(menu);
}

/** Launch the quiz (from the /quiz command or the onboarding button). */
export async function startQuiz(interaction) {
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });
  let quiz;
  let neurotypes;
  try {
    [quiz, neurotypes] = await Promise.all([getQuiz(), getNeurotypes()]);
  } catch (err) {
    console.error('quiz start fetch failed:', err);
    return interaction.editReply({ content: 'The typology quiz is unavailable right now. Try again shortly.' });
  }
  const session = startSession(interaction.user.id, quiz, neurotypes.neurotypes);
  return interaction.editReply({ embeds: [questionEmbed(session)], components: [answerRow(session)] });
}

/** A question was answered — record it and advance, or finish + score. */
export async function handleAnswer(interaction) {
  const session = getSession(interaction.user.id);
  if (!session) {
    return interaction.reply({
      content: 'Your quiz session expired. Run `/quiz` to start again.',
      flags: MessageFlags.Ephemeral,
    });
  }

  const question = session.questions[session.index];
  session.answers[question.id] = interaction.values[0];
  session.index += 1;

  if (session.index < session.questions.length) {
    return interaction.update({ embeds: [questionEmbed(session)], components: [answerRow(session)] });
  }

  // Finished — acknowledge, score server-side, then show the result.
  await interaction.update({
    embeds: [new EmbedBuilder().setColor(ACCENT).setTitle('Scoring…').setDescription('Reading your answers.')],
    components: [],
  });

  let outcome;
  try {
    outcome = await submitQuiz(interaction.user.id, session.answers, session.version);
  } catch (err) {
    console.error('quiz submit failed:', err);
    return interaction.editReply({
      content: 'Could not save your result. Make sure you have onboarded (profile exists), then run `/quiz` again.',
      embeds: [],
      components: [],
    });
  }

  const result = outcome.result;
  const top = result.top;
  const meta = session.neurotypes[top] ?? {};
  const topThree = (result.top3 ?? [])
    .map((id) => session.neurotypes[id]?.label ?? id)
    .join(', ');

  const embed = new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle(`Assessed archetype: ${meta.emoji ?? ''} ${meta.label ?? top}`.trim())
    .setDescription(
      [
        meta.tagline ?? '',
        topThree ? `\nClosest three: **${topThree}**` : '',
        '\nThat’s the network’s read on you. Now — which one do **you** identify as? Pick below and both badges are saved.',
      ]
        .filter(Boolean)
        .join('\n'),
    );

  return interaction.editReply({ embeds: [embed], components: [identifyRow(session.neurotypes)] });
}

/** Self-identified badge chosen. */
export async function handleIdentify(interaction) {
  const chosen = interaction.values[0];
  const session = getSession(interaction.user.id);
  const neurotypes = session?.neurotypes ?? {};

  try {
    await setIdentified(interaction.user.id, chosen);
  } catch (err) {
    console.error('set identified failed:', err);
    return interaction.update({
      content: 'Could not save that choice — your assessed badge is still stored. Try `/quiz` again later.',
      embeds: [],
      components: [],
    });
  }

  endSession(interaction.user.id);
  const meta = neurotypes[chosen] ?? {};
  const embed = new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle('All set ✨')
    .setDescription(
      `You identify as ${meta.emoji ?? ''} **${meta.label ?? chosen}**. `.trim() +
        '\nYour assessed and identified badges are saved — they’ll show on your profile and the network map.',
    );
  return interaction.update({ embeds: [embed], components: [] });
}
