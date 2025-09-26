import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils import parse_duration
from .hybrid_helpers import add_prefix_command
from db.DBHelper import (
    set_anti_nuke_setting,
    get_anti_nuke_setting,
    add_safe_user,
    remove_safe_user,
    get_safe_users,
    add_safe_role,
    remove_safe_role,
    get_safe_roles,
    set_anti_nuke_log_channel,
    get_anti_nuke_log_channel,
)

OWNER_ID = 756537363509018736

CATEGORIES = [
    "delete_roles",
    "add_roles",
    "kick",
    "ban",
    "delete_channels",
    "anti_mention",
    "webhook",
]


def setup(bot: commands.Bot):
    @bot.tree.command(name="antinukeconfig", description="Configure anti nuke category")
    @app_commands.describe(
        category="Category",
        threshold="Actions before trigger",
        punishment="timeout/strip/kick/ban",
        duration="Timeout duration (e.g. 60s, 5m)",
        enabled="Enable protection",
    )
    async def antinukeconfig(
        interaction: discord.Interaction,
        category: str,
        threshold: int,
        punishment: str,
        duration: Optional[str],
        enabled: bool,
    ):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        if category not in CATEGORIES:
            await interaction.response.send_message("Invalid category.", ephemeral=True)
            return
        dur_s = parse_duration(duration) if duration else None
        set_anti_nuke_setting(
            category, int(enabled), threshold, punishment, dur_s, interaction.guild.id
        )
        await interaction.response.send_message("Saved.", ephemeral=True)

    @bot.tree.command(name="antinukeignoreuser", description="Toggle safe user")
    async def antinukeignoreuser(interaction: discord.Interaction, user: discord.Member):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        guild_id = interaction.guild.id
        if user.id in get_safe_users(guild_id):
            remove_safe_user(guild_id, user.id)
            await interaction.response.send_message("User removed from safe list.", ephemeral=True)
        else:
            add_safe_user(guild_id, user.id)
            await interaction.response.send_message("User added to safe list.", ephemeral=True)

    @bot.tree.command(name="antinukeignorerole", description="Toggle safe role")
    async def antinukeignorerole(interaction: discord.Interaction, role: discord.Role):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        guild_id = interaction.guild.id
        if role.id in get_safe_roles(guild_id):
            remove_safe_role(guild_id, role.id)
            await interaction.response.send_message("Role removed from safe list.", ephemeral=True)
        else:
            add_safe_role(guild_id, role.id)
            await interaction.response.send_message("Role added to safe list.", ephemeral=True)

    @bot.tree.command(name="antinukelog", description="Set anti nuke log channel")
    async def antinukelog(interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        set_anti_nuke_log_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            f"Log channel set to {channel.mention}", ephemeral=True
        )

    @bot.tree.command(name="antinukesettings", description="Show anti nuke configuration")
    async def antinukesettings(interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        lines = []
        gid = interaction.guild.id
        for cat in CATEGORIES:
            setting = get_anti_nuke_setting(cat, gid)
            if setting:
                en, th, p, dur = setting
                desc = f"on" if en else "off"
                desc += f", threshold={th}, punishment={p}"
                if p == "timeout" and dur:
                    desc += f" {dur}s"
            else:
                desc = "not set"
            lines.append(f"**{cat}**: {desc}")

        users = [f"<@{u}>" for u in get_safe_users(gid)] or ["None"]
        roles = [f"<@&{r}>" for r in get_safe_roles(gid)] or ["None"]
        cid = get_anti_nuke_log_channel(gid)
        log_line = f"<#{cid}>" if cid else "None"
        lines.append(f"Safe users: {', '.join(users)}")
        lines.append(f"Safe roles: {', '.join(roles)}")
        lines.append(f"Log channel: {log_line}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    add_prefix_command(bot, antinukeconfig)
    add_prefix_command(bot, antinukeignoreuser)
    add_prefix_command(bot, antinukeignorerole)
    add_prefix_command(bot, antinukelog)
    add_prefix_command(bot, antinukesettings)

