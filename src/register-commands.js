import { REST, Routes, SlashCommandBuilder } from 'discord.js';
import 'dotenv/config';
import { config } from './config.js';

const commands = [
  new SlashCommandBuilder()
    .setName('setup-onboarding')
    .setDescription('Post the Zima onboarding message in this channel (admin only)')
    .setDefaultMemberPermissions(0x8), // Administrator
  new SlashCommandBuilder()
    .setName('quiz')
    .setDescription('Take the Zima typology quiz to find your archetype'),
].map((c) => c.toJSON());

const rest = new REST({ version: '10' }).setToken(config.discordToken);

const route = config.serverId
  ? Routes.applicationGuildCommands(config.applicationId, config.serverId)
  : Routes.applicationCommands(config.applicationId);

try {
  await rest.put(route, { body: commands });
  console.log(`Registered ${commands.length} command(s).`);
  if (config.serverId) {
    console.log(`Server: ${config.serverId}`);
  } else {
    console.log('Registered globally (can take up to an hour to appear).');
  }
} catch (err) {
  if (err.code === 50001) {
    console.error(`
Discord returned "Missing Access" (50001) while registering slash commands.

This almost always means the bot is not in the server listed as DISCORD_SERVER_ID,
or your .env IDs do not match the same Discord application as DISCORD_TOKEN.

Checklist:
  1. DISCORD_APPLICATION_ID = Developer Portal → General Information → Application ID
  2. DISCORD_TOKEN = same app → Bot → Token (reset if unsure)
  3. DISCORD_SERVER_ID = right-click YOUR server icon → Copy Server ID
  4. Re-invite the bot to that server:
     Developer Portal → OAuth2 → URL Generator
     Scopes: bot, applications.commands
     Bot permissions: Manage Roles, Send Messages, View Channels
     Open the generated URL and add the bot to the server.
  5. Confirm the bot appears in the server member list, then run:
     npm run register-commands

Application ID used: ${config.applicationId}
Server ID used: ${config.serverId ?? '(none — global register)'}
`);
    process.exit(1);
  }
  throw err;
}
