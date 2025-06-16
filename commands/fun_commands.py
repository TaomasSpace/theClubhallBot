import discord
from discord import app_commands
from discord.ext import commands

lowercase_locked: set[int] = set()


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="forcelowercase", description="Force a member's messages to lowercase (toggle)"
    )
    @app_commands.describe(member="Member to lock/unlock")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def forcelowercase(interaction: discord.Interaction, member: discord.Member):
        if member.id in lowercase_locked:
            lowercase_locked.remove(member.id)
            await interaction.response.send_message(
                f"🔓 {member.display_name} unlocked – messages stay unchanged.",
                ephemeral=True,
            )
        else:
            lowercase_locked.add(member.id)
            await interaction.response.send_message(
                f"🔒 {member.display_name} locked – messages will be lower-cased.",
                ephemeral=True,
            )

    return forcelowercase
