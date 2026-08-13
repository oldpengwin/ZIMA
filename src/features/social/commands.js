// Social slash commands for the ZIMA bot: /profile, /matches, /projects,
// /connect. All read/act through the Python API (src/lib/apiClient.js) with the
// bot service key — the bot holds no DB credentials and no scoring logic. All
// replies are ephemeral so the channel stays clean.
import { EmbedBuilder, MessageFlags } from 'discord.js';
import {
  connectBuilders,
  getMatches,
  getProfileByDiscordId,
  listProjects,
} from '../../lib/apiClient.js';

const ACCENT = 0x4fb477;
const EPHEMERAL = { flags: MessageFlags.Ephemeral };

function titleize(s) {
  if (!s) return '—';
  return String(s).charAt(0).toUpperCase() + String(s).slice(1);
}

/** /profile [user] — a builder's public archetype card (yours by default). */
export async function handleProfile(interaction) {
  await interaction.deferReply(EPHEMERAL);
  const target = interaction.options.getUser('user') || interaction.user;
  let profile;
  try {
    profile = await getProfileByDiscordId(target.id);
  } catch (err) {
    console.error('/profile fetch failed:', err);
    return interaction.editReply({ content: "Couldn't load that profile right now — try again shortly." });
  }
  if (!profile) {
    const who = target.id === interaction.user.id ? "You haven't" : `${target.username} hasn't`;
    return interaction.editReply({ content: `${who} onboarded on ZIMA yet.` });
  }
  const embed = new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle(profile.display_name || target.username)
    .setDescription(profile.tagline || profile.bio || 'A ZIMA builder.')
    .addFields(
      { name: 'Archetype', value: profile.neurotype ? titleize(profile.neurotype) : 'Not yet assessed', inline: true },
      { name: 'Open to connect', value: profile.is_open ? 'Yes' : 'No', inline: true },
    );
  if (profile.skills && profile.skills.length) {
    embed.addFields({ name: 'Skills', value: profile.skills.slice(0, 10).join(', ').slice(0, 1000) });
  }
  return interaction.editReply({ embeds: [embed] });
}

/** /matches — the caller's top neurotype matches. */
export async function handleMatches(interaction) {
  await interaction.deferReply(EPHEMERAL);
  let data;
  try {
    data = await getMatches(interaction.user.id, 5);
  } catch (err) {
    console.error('/matches fetch failed:', err);
    const msg = /onboard|quiz|archetype/i.test(err.message)
      ? 'Take the archetype quiz first (`/quiz`) so we can match you.'
      : "Couldn't load your matches right now — try again shortly.";
    return interaction.editReply({ content: msg });
  }
  if (!data.matches || !data.matches.length) {
    return interaction.editReply({ content: 'No matches yet — check back as more builders join.' });
  }
  const embed = new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle('Your top matches')
    .setDescription(
      data.matches
        .map((m, i) => {
          const pct = Math.round((m.score || 0) * 100);
          const line = `**${i + 1}. ${m.display_name}** — ${titleize(m.neurotype)} · ${pct}% fit`;
          return m.tagline ? `${line}\n   _${m.tagline}_` : line;
        })
        .join('\n'),
    )
    .setFooter({ text: 'Use /connect to reach out.' });
  return interaction.editReply({ embeds: [embed] });
}

/** /projects — browse open projects. */
export async function handleProjects(interaction) {
  await interaction.deferReply(EPHEMERAL);
  let projects;
  try {
    projects = await listProjects(10);
  } catch (err) {
    console.error('/projects fetch failed:', err);
    return interaction.editReply({ content: "Couldn't load projects right now — try again shortly." });
  }
  if (!projects || !projects.length) {
    return interaction.editReply({ content: 'No open projects yet. Start one on the platform!' });
  }
  const embed = new EmbedBuilder()
    .setColor(ACCENT)
    .setTitle('Open projects')
    .setDescription(
      projects
        .slice(0, 10)
        .map((p) => {
          const needs = (p.skills_needed || []).slice(0, 4).join(', ');
          const line = `**${p.title}** — ${p.status || 'idea'}`;
          return needs ? `${line}\n   needs: ${needs}` : line;
        })
        .join('\n'),
    );
  return interaction.editReply({ embeds: [embed] });
}

/** /connect <user> [message] — send a connection request. */
export async function handleConnect(interaction) {
  await interaction.deferReply(EPHEMERAL);
  const target = interaction.options.getUser('user');
  const message = interaction.options.getString('message') || '';
  if (!target) {
    return interaction.editReply({ content: 'Pick a builder to connect with.' });
  }
  if (target.id === interaction.user.id) {
    return interaction.editReply({ content: "You can't connect with yourself." });
  }
  if (target.bot) {
    return interaction.editReply({ content: "That's a bot — pick a real builder." });
  }
  try {
    await connectBuilders({ fromDiscordId: interaction.user.id, toDiscordId: target.id, message });
  } catch (err) {
    console.error('/connect failed:', err);
    let msg = "Couldn't send that connection request right now — try again shortly.";
    if (/already exists/i.test(err.message)) msg = `You already have a connection request with ${target.username}.`;
    else if (/profile first|onboard/i.test(err.message)) msg = 'You need a ZIMA profile first — onboard on the server.';
    else if (/isn't on zima|does not exist|not found/i.test(err.message)) msg = `${target.username} isn't on ZIMA yet.`;
    return interaction.editReply({ content: msg });
  }
  return interaction.editReply({ content: `Connection request sent to **${target.username}**. They've been notified.` });
}
