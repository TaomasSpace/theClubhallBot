import discord
from discord import app_commands
from discord.ext import commands

from db.DBHelper import get_command_permission


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="explain", description="Explain a bot command and its permissions"
    )
    @app_commands.describe(command="Command to explain")
    async def explain(interaction: discord.Interaction, command: str):
        cmd = bot.tree.get_command(command)
        if cmd is None:
            await interaction.response.send_message("Unknown command.", ephemeral=True)
            return

        guild = interaction.guild
        role_mention = "No specific role required"
        if guild is not None:
            role_id = get_command_permission(guild.id, command)
            if role_id is not None:
                role = guild.get_role(role_id)
                if role is not None:
                    role_mention = role.mention
                else:
                    role_mention = f"Role ID {role_id}"

        params_lines: list[str] = []
        for param in cmd.parameters:
            name = getattr(param, "name", "")
            if name in ("self", "interaction"):
                continue
            desc = getattr(param, "description", None) or "No description"
            params_lines.append(f"`{name}`: {desc}")
        params_info = "\n".join(params_lines) if params_lines else "None"

        await interaction.response.send_message(
            f"**/{cmd.name}** - {cmd.description}\n"
            f"**Parameters:**\n{params_info}\n"
            f"**Required Role:** {role_mention}",
            ephemeral=True,
        )

    @explain.autocomplete("command")
    async def explain_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        commands_list = []
        for c in bot.tree.get_commands():
            if current.lower() in c.name.lower():
                commands_list.append(app_commands.Choice(name=c.name, value=c.name))
        return commands_list[:25]
