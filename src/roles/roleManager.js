import { roleKeys } from '../config.js';
import { recordRoleGrant } from '../lib/apiClient.js';

export class RoleGrantError extends Error {
  constructor(message, { userMessage } = {}) {
    super(message);
    this.name = 'RoleGrantError';
    this.userMessage = userMessage ?? message;
  }
}

function explainRoleGrantFailure(member, role) {
  const me = member.guild.members.me;
  if (!me?.permissions.has('ManageRoles')) {
    return 'The bot is missing the **Manage Roles** permission. Re-invite the bot with that permission, or enable it in Server Settings → Roles.';
  }

  if (me.roles.highest.position <= role.position) {
    return [
      'The bot’s role must be **above** the Vetted role in the server role list.',
      'Server Settings → Roles → drag the bot role higher than **Vetted**, then try again.',
    ].join(' ');
  }

  if (member.roles.highest.position >= me.roles.highest.position) {
    return 'Zima cannot assign roles to members who are ranked at or above the bot’s highest role.';
  }

  if (role.managed) {
    return 'The Vetted role is managed by an integration and cannot be assigned by Zima. Use a normal custom role for **Vetted**.';
  }

  return 'Discord blocked assigning the Vetted role. Check that the bot has **Manage Roles** and sits above **Vetted** in the role list.';
}

export async function grantRole(member, roleKey, { source = 'system', metadata = {} } = {}) {
  const roleId = roleKeys[roleKey];
  if (!roleId) {
    throw new RoleGrantError(`Unknown role key: ${roleKey}`);
  }

  const role = member.guild.roles.cache.get(roleId);
  if (!role) {
    throw new RoleGrantError(`Role ${roleKey} (${roleId}) not found in this server. Check VETTED_ROLE_ID in .env.`);
  }

  const me = member.guild.members.me;
  if (!me?.permissions.has('ManageRoles')) {
    throw new RoleGrantError('Missing Manage Roles', {
      userMessage: explainRoleGrantFailure(member, role),
    });
  }

  if (me.roles.highest.position <= role.position || role.managed) {
    throw new RoleGrantError('Role hierarchy or managed role', {
      userMessage: explainRoleGrantFailure(member, role),
    });
  }

  if (!member.roles.cache.has(roleId)) {
    try {
      await member.roles.add(role, `Zima: granted ${roleKey}`);
    } catch (err) {
      if (err.code === 50013) {
        throw new RoleGrantError(err.message, {
          userMessage: explainRoleGrantFailure(member, role),
        });
      }
      throw err;
    }
  }

  await recordRoleGrant({
    discordId: member.id,
    roleKey,
    source,
    metadata,
  });

  return role;
}

/** Future: map quest_key -> role_key and grant on completion */
export const questRoleMap = {
  // example: first_quest: 'explorer',
};
