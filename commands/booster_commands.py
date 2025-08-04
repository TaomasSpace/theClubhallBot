import discord
from discord import app_commands
from discord.ext import commands
from db.DBHelper import get_custom_role, set_custom_role


def setup(bot: commands.Bot):
    @bot.tree.command(name="customrole", description="Create or update your booster role")
    @app_commands.describe(name="Name of your role", color="Hex color like #FFAA00")
    async def customrole(interaction: discord.Interaction, name: str, color: str):
        member = interaction.user
        guild = interaction.guild

        if not member.premium_since:
            await interaction.response.send_message(
                "❌ This command is only for server boosters!", ephemeral=True
            )
            return

        try:
            colour_obj = discord.Colour(int(color.lstrip("#"), 16))
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Invalid color. Use hex like #FFAA00", ephemeral=True
            )
            return

        role_id = get_custom_role(guild.id, str(member.id))

        if role_id:
            role = guild.get_role(role_id)
            if role:
                await role.edit(name=name, colour=colour_obj)
                await interaction.response.send_message(
                    f"🔄 Your role has been updated to **{name}**.", ephemeral=True
                )
                return

        try:
            role = await guild.create_role(
                name=name, colour=colour_obj, reason="Custom booster role"
            )
            await member.add_roles(role, reason="Assigned custom booster role")
            set_custom_role(guild.id, str(member.id), role.id)
            await interaction.response.send_message(
                f"✅ Custom role **{name}** created and assigned!", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I need permission to manage roles.", ephemeral=True
            )

    @bot.tree.command(
        name="grantrole",
        description="Give your custom role to another user",
    )
    @app_commands.describe(target="User to give your custom role to")
    async def grantrole(interaction: discord.Interaction, target: discord.Member):
        booster_id = str(interaction.user.id)
        target_id = str(target.id)

        if booster_id == target_id:
            await interaction.response.send_message(
                "You can't give your role to yourself.", ephemeral=True
            )
            return

        role_id = get_custom_role(interaction.guild.id, booster_id)
        if not role_id:
            await interaction.response.send_message(
                "You don't have a custom role.", ephemeral=True
            )
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(
                "Your custom role was not found.", ephemeral=True
            )
            return

        await target.add_roles(role, reason="Booster shared custom role")
        await interaction.response.send_message(
            f"✅ {target.display_name} got your role **{role.name}**.", ephemeral=False
        )

    return customrole, grantrole
