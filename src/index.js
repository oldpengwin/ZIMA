import {
  Client,
  Events,
  GatewayIntentBits,
  MessageFlags,
  Partials,
} from 'discord.js';
import { config } from './config.js';
import { postOnboardingMessage } from './features/onboarding/flow.js';
import { onGuildMemberAdd } from './handlers/guildMemberAdd.js';
import { onInteractionCreate } from './handlers/interactionCreate.js';

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
  ],
  partials: [Partials.GuildMember],
});

client.once(Events.ClientReady, (c) => {
  console.log(`Zima logged in as ${c.user.tag}`);
});

client.on(Events.GuildMemberAdd, (member) => {
  onGuildMemberAdd(member).catch((err) => console.error('guildMemberAdd:', err));
});

client.on(Events.InteractionCreate, (interaction) => {
  if (interaction.isChatInputCommand() && interaction.commandName === 'setup-onboarding') {
    return postOnboardingMessage(interaction.channel)
      .then(() =>
        interaction.reply({
          content: 'Onboarding message posted.',
          flags: MessageFlags.Ephemeral,
        }),
      )
      .catch((err) => {
        console.error('setup-onboarding:', err);
        return interaction.reply({
          content: 'Failed to post onboarding message.',
          flags: MessageFlags.Ephemeral,
        });
      });
  }

  onInteractionCreate(interaction).catch((err) => {
    console.error('interaction:', err);
    if (interaction.isRepliable() && !interaction.replied && !interaction.deferred) {
      interaction
        .reply({ content: 'Something went wrong.', flags: MessageFlags.Ephemeral })
        .catch(() => {});
    }
  });
});

client.login(config.discordToken).catch((err) => {
  if (err.message?.includes('disallowed intents')) {
    console.error(`
Zima could not connect: privileged intents are disabled in the Developer Portal.

Enable **Server Members Intent** (required for welcome pings when someone joins):
  Developer Portal → your app → Bot → Privileged Gateway Intents
  → turn on "SERVER MEMBERS INTENT" → Save

Then restart: npm run dev
`);
  }
  throw err;
});
