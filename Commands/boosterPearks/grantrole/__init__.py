import discord
from db.DBHelper import get_custom_role

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
