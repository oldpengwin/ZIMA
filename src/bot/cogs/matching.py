"""
Discord Cog for Matching Commands

Implements matching functionality for the ZIMA Discord bot.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Any
import logging
import uuid

from ....core.neurotype_matcher import NeurotypeMatcher, Profile, Neurotype
from ....core.profile_manager import ProfileManager, ProfileNotFoundError


class MatchingCog(commands.Cog):
    """
    Discord cog for user matching functionality

    Provides commands for finding compatible builders based on neurotypes
    and skills, and managing connection requests.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initialize matching cog

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        # Initialize profile manager
        # In production, this would use dependency injection
        self.profile_manager = ProfileManager(db_url="postgresql://user:password@localhost/zima")

    @app_commands.command(name="match", description="Find compatible builders based on your profile")
    @app_commands.describe(limit="Number of matches to show (1-10)")
    async def match_command(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 5
    ) -> None:
        """
        Find and display compatible matches for the user

        Args:
            interaction: Discord interaction
            limit: Number of matches to show
        """
        await interaction.response.defer(ephemeral=True)

        try:
            # Get user profile
            user_profile = self.profile_manager.get_profile_by_discord_id(str(interaction.user.id))

            if not user_profile:
                await interaction.followup.send(
                    "You need to complete onboarding first. Use `/onboard` to create your profile.",
                    ephemeral=True
                )
                return

            # Validate limit
            if limit is None:
                limit = 5
            elif limit < 1 or limit > 10:
                limit = max(1, min(10, limit))

            # Get all profiles for matching
            all_profiles = self.profile_manager.get_all_profiles()

            if len(all_profiles) <= 1:
                await interaction.followup.send(
                    "Not enough profiles available for matching yet. Check back later!",
                    ephemeral=True
                )
                return

            # Create matcher and find top matches
            matcher = NeurotypeMatcher(all_profiles)
            matches = matcher.find_top_matches(str(user_profile.id), limit)

            if not matches:
                await interaction.followup.send(
                    "No matches found. Try updating your profile with more skills and what you're looking for.",
                    ephemeral=True
                )
                return

            # Format response
            embed = discord.Embed(
                title=f"🔍 Top Matches for {user_profile.display_name}",
                description=f"Found {len(matches)} compatible builders based on your profile",
                color=discord.Color.blue()
            )

            for i, match in enumerate(matches, 1):
                profile = match["profile"]
                score = match["score"]["total"]

                embed.add_field(
                    name=f"{i}. {profile.display_name} ({profile.neurotype.value})",
                    value=(
                        f"**Match Score**: {(score * 100):.1f}%\n"
                        f"**Location**: {profile.location or 'Not specified'}\n"
                        f"**Skills**: {', '.join(profile.skills[:3]) if profile.skills else 'None listed'}\n"
                        f"**Looking for**: {', '.join(profile.looking_for[:2]) if profile.looking_for else 'Not specified'}"
                    ),
                    inline=False
                )

            embed.set_footer(text="Use /connect to reach out to these builders!")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Match command error: {e}")
            await interaction.followup.send(
                "An error occurred while finding matches. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="connect", description="Connect with another builder")
    @app_commands.describe(
        user="Discord ID or mention of the user to connect with",
        message="Optional message to include with your connection request"
    )
    async def connect_command(
        self,
        interaction: discord.Interaction,
        user: str,
        message: Optional[str] = None
    ) -> None:
        """
        Send a connection request to another user

        Args:
            interaction: Discord interaction
            user: User to connect with (ID or mention)
            message: Optional message
        """
        await interaction.response.defer(ephemeral=True)

        try:
            # Extract user ID from mention if needed
            user_id = user
            if user.startswith('<@') and user.endswith('>'):
                user_id = user[2:-1]
                if user_id.startswith('!'):
                    user_id = user_id[1:]

            # Get both profiles
            from_profile = self.profile_manager.get_profile_by_discord_id(str(interaction.user.id))
            to_profile = self.profile_manager.get_profile_by_discord_id(user_id)

            if not from_profile:
                await interaction.followup.send(
                    "You need to complete onboarding first. Use `/onboard` to create your profile.",
                    ephemeral=True
                )
                return

            if not to_profile:
                await interaction.followup.send(
                    f"User with ID {user_id} not found or hasn't completed onboarding.",
                    ephemeral=True
                )
                return

            if str(to_profile.id) == str(from_profile.id):
                await interaction.followup.send(
                    "You can't connect with yourself!",
                    ephemeral=True
                )
                return

            # In a real implementation, this would create a database record
            # For now, we'll simulate it and send a DM
            connection_id = str(uuid.uuid4())
            request_message = message or f"{from_profile.display_name} wants to connect with you on ZIMA!"

            # Create embed for the request
            embed = discord.Embed(
                title="🔗 New Connection Request",
                description=request_message,
                color=discord.Color.green()
            )

            embed.add_field(name="From", value=f"{from_profile.display_name} ({from_profile.neurotype.value})", inline=False)
            embed.add_field(name="Skills", value=', '.join(from_profile.skills[:5]) if from_profile.skills else "None listed", inline=False)
            embed.add_field(name="Looking for", value=', '.join(from_profile.looking_for[:3]) if from_profile.looking_for else "Not specified", inline=False)

            embed.set_footer(text=f"Request ID: {connection_id}")

            # Try to send DM to the target user
            try:
                target_user = await self.bot.fetch_user(int(user_id))
                await target_user.send(embed=embed)

                # Send confirmation to requester
                confirm_embed = discord.Embed(
                    title="✅ Connection Request Sent",
                    description=f"Your request has been sent to {to_profile.display_name}",
                    color=discord.Color.green()
                )

                await interaction.followup.send(embed=confirm_embed, ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send(
                    f"Could not send DM to {to_profile.display_name} (they may have DMs disabled).",
                    ephemeral=True
                )
            except Exception as dm_error:
                self.logger.error(f"Failed to send DM: {dm_error}")
                await interaction.followup.send(
                    "Failed to send connection request. The user may have DMs disabled.",
                    ephemeral=True
                )

        except Exception as e:
            self.logger.error(f"Connect command error: {e}")
            await interaction.followup.send(
                "An error occurred while sending the connection request. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="my-matches", description="View your recent connection requests and matches")
    async def my_matches_command(self, interaction: discord.Interaction) -> None:
        """
        Show user's connection requests and matches

        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(ephemeral=True)

        try:
            # Get user profile
            user_profile = self.profile_manager.get_profile_by_discord_id(str(interaction.user.id))

            if not user_profile:
                await interaction.followup.send(
                    "You need to complete onboarding first. Use `/onboard` to create your profile.",
                    ephemeral=True
                )
                return

            # In a real implementation, this would query the database
            # For now, we'll show a placeholder response
            embed = discord.Embed(
                title=f"🔗 Your Connections",
                description=f"Connection activity for {user_profile.display_name}",
                color=discord.Color.purple()
            )

            embed.add_field(
                name="Pending Requests",
                value="No pending connection requests",
                inline=False
            )

            embed.add_field(
                name="Accepted Connections",
                value="No accepted connections yet",
                inline=False
            )

            embed.set_footer(text="Use /match to find new builders to connect with!")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"My matches command error: {e}")
            await interaction.followup.send(
                "An error occurred while retrieving your connections. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="neurotypes", description="Learn about the different neurotypes")
    @app_commands.describe(neurotype="Specific neurotype to learn about (optional)")
    async def neurotypes_command(
        self,
        interaction: discord.Interaction,
        neurotype: Optional[str] = None
    ) -> None:
        """
        Display information about neurotypes

        Args:
            interaction: Discord interaction
            neurotype: Optional specific neurotype to show
        """
        await interaction.response.defer(ephemeral=True)

        try:
            if neurotype:
                # Show specific neurotype
                try:
                    nt = Neurotype(neurotype.lower())
                    embed = self._create_neurotype_embed(nt)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except ValueError:
                    await interaction.followup.send(
                        f"Unknown neurotype: {neurotype}. Available neurotypes: {', '.join([nt.value for nt in Neurotype])}",
                        ephemeral=True
                    )
            else:
                # Show all neurotypes
                embed = discord.Embed(
                    title="🧠 ZIMA Neurotypes",
                    description="The 10 neurotypes that form the foundation of the ZIMA network",
                    color=discord.Color.blurple()
                )

                for nt in Neurotype:
                    embed.add_field(
                        name=f"{nt.value.capitalize()} ({self._get_neurotype_emoji(nt)})",
                        value=self._get_neurotype_description(nt)[:100] + "...",
                        inline=False
                    )

                embed.set_footer(text="Use /neurotypes [name] to learn more about a specific neurotype")
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Neurotypes command error: {e}")
            await interaction.followup.send(
                "An error occurred while retrieving neurotype information.",
                ephemeral=True
            )

    def _create_neurotype_embed(self, neurotype: Neurotype) -> discord.Embed:
        """Create embed for a specific neurotype"""
        embed = discord.Embed(
            title=f"{neurotype.value.capitalize()} {self._get_neurotype_emoji(neurotype)}",
            description=self._get_neurotype_description(neurotype),
            color=self._get_neurotype_color(neurotype)
        )

        # Add skills
        skills = self._get_neurotype_skills(neurotype)
        if skills:
            embed.add_field(name="Key Skills", value='\n'.join(f"• {skill}" for skill in skills), inline=False)

        # Add compatibility info
        embed.add_field(
            name="Compatible With",
            value=self._get_compatible_neurotypes(neurotype),
            inline=False
        )

        return embed

    def _get_neurotype_emoji(self, neurotype: Neurotype) -> str:
        """Get emoji for neurotype"""
        emojis = {
            Neurotype.SEEDCASTER: "🌱",
            Neurotype.FABRICANT: "⚙️",
            Neurotype.MYCELIAN: "🍄",
            Neurotype.TERRAFORMER: "🏗️",
            Neurotype.DEVELOPER: "💻",
            Neurotype.ARTISAN: "🎨",
            Neurotype.CHRONICLER: "📡",
            Neurotype.CULTIVAR: "🌿",
            Neurotype.LOOMKEEPER: "🔗",
            Neurotype.VERDANT: "📜"
        }
        return emojis.get(neurotype, "❓")

    def _get_neurotype_description(self, neurotype: Neurotype) -> str:
        """Get description for neurotype"""
        descriptions = {
            Neurotype.SEEDCASTER: "They plant what others haven't imagined yet. Seedcasters are the visionaries of regenerative systems, food forests, and sustainable agriculture.",
            Neurotype.FABRICANT: "If it doesn't exist, they build it. Fabricants are the makers, engineers, and builders who create physical solutions to complex problems.",
            Neurotype.MYCELIAN: "They think in networks and grow in the dark. Mycelians work with biological systems, chemistry, and ecological processes.",
            Neurotype.TERRAFORMER: "They redesign the spaces we inhabit. Terraformers are architects, urban planners, and designers of sustainable living environments.",
            Neurotype.DEVELOPER: "They write the tools of sovereignty. Developers create software, automation, and digital infrastructure.",
            Neurotype.ARTISAN: "They make the future beautiful enough to want. Artisans combine aesthetics, craftsmanship, and design.",
            Neurotype.CHRONICLER: "They make sure the work gets seen. Chroniclers are storytellers, media creators, and community archivists.",
            Neurotype.CULTIVAR: "They bridge the lab and the land. Cultivars work at the intersection of science and practical application.",
            Neurotype.LOOMKEEPER: "They hold the network together. Loomkeepers are community builders, organizers, and connectors.",
            Neurotype.VERDANT: "They change the rules of the game. Verdants work on policy, advocacy, and systemic change."
        }
        return descriptions.get(neurotype, "Unknown neurotype")

    def _get_neurotype_skills(self, neurotype: Neurotype) -> List[str]:
        """Get typical skills for neurotype"""
        skills_map = {
            Neurotype.SEEDCASTER: [
                "Regenerative agriculture", "Composting systems", "Food forests",
                "Urban farming", "Seed saving", "Agroforestry"
            ],
            Neurotype.FABRICANT: [
                "Mechanical engineering", "Fabrication", "Prototyping",
                "CAD/CAM", "Open-source hardware", "Maker culture"
            ],
            Neurotype.MYCELIAN: [
                "Biology", "Chemistry", "Biomaterials", "Fermentation",
                "Ecological science", "Bioremediation"
            ],
            Neurotype.TERRAFORMER: [
                "Sustainable architecture", "Passive design", "Urban ecology",
                "Community land trusts", "Natural building"
            ],
            Neurotype.DEVELOPER: [
                "Software engineering", "AI/ML", "Data pipelines",
                "Web development", "Automation", "Prompt engineering"
            ],
            Neurotype.ARTISAN: [
                "Visual design", "Fabrication", "Textile/material work",
                "UI/UX", "Solarpunk aesthetics", "World-building"
            ],
            Neurotype.CHRONICLER: [
                "Storytelling", "Video production", "Writing",
                "Social media", "Community media", "Archiving"
            ],
            Neurotype.CULTIVAR: [
                "Food science", "Plant medicine", "Nutrition systems",
                "Crop research", "Soil biology"
            ],
            Neurotype.LOOMKEEPER: [
                "Community building", "Event production", "Fundraising",
                "Partnerships", "Grassroots organizing"
            ],
            Neurotype.VERDANT: [
                "Policy", "Advocacy", "Circular economics",
                "Environmental law", "Systems governance", "Funding strategy"
            ]
        }
        return skills_map.get(neurotype, [])

    def _get_neurotype_color(self, neurotype: Neurotype) -> discord.Color:
        """Get color for neurotype - aligned with HOPAMINE brand guidelines"""
        # HOPAMINE brand colors
        colors = {
            Neurotype.SEEDCASTER: discord.Color.from_rgb(0x57, 0xB8, 0xDC),  # Sky blue (primary)
            Neurotype.FABRICANT: discord.Color.from_rgb(0x1E, 0x61, 0x93),  # Deep ocean blue
            Neurotype.MYCELIAN: discord.Color.from_rgb(0xA4, 0xC2, 0x4B),  # Lime
            Neurotype.TERRAFORMER: discord.Color.from_rgb(0xDE, 0x7A, 0x48),  # Clay orange
            Neurotype.DEVELOPER: discord.Color.from_rgb(0x57, 0xB8, 0xDC),  # Sky blue
            Neurotype.ARTISAN: discord.Color.from_rgb(0xE9, 0x3C, 0xA7),  # Hot magenta (accent)
            Neurotype.CHRONICLER: discord.Color.from_rgb(0xE9, 0x3C, 0xA7),  # Hot magenta
            Neurotype.CULTIVAR: discord.Color.from_rgb(0xA4, 0xC2, 0x4B),  # Lime
            Neurotype.LOOMKEEPER: discord.Color.from_rgb(0xE9, 0x3C, 0xA7),  # Hot magenta
            Neurotype.VERDANT: discord.Color.from_rgb(0x1E, 0x61, 0x93)  # Deep ocean blue
        }
        return colors.get(neurotype, discord.Color.from_rgb(0x57, 0xB8, 0xDC))  # Default to sky blue

    def _get_compatible_neurotypes(self, neurotype: Neurotype) -> str:
        """Get compatible neurotypes"""
        from ..core.neurotype_matcher import NeurotypeMatcher

        compatibilities = []
        for other_nt in Neurotype:
            if other_nt == neurotype:
                continue
            score = NeurotypeMatcher.COMPATIBILITY_MATRIX.get(neurotype, {}).get(other_nt, 0.5)
            if score >= 0.7:
                compatibilities.append(f"{other_nt.value} ({score:.1f})")

        return ', '.join(compatibilities) if compatibilities else "All neurotypes"


async def setup(bot: commands.Bot) -> None:
    """Add cog to bot"""
    await bot.add_cog(MatchingCog(bot))