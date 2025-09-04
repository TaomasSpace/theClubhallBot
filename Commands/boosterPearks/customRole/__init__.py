import discord
from db.DBHelper import get_custom_role, set_custom_role

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
