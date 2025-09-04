import discord
from db.DBHelper import register_user, safe_add_coins
from utils import has_command_permission

async def addMoney(
    interaction: discord.Interaction, user: discord.Member, amount: int
) -> None:
    if not has_command_permission(interaction.user, "addmoney", "admin"):
        await interaction.response.send_message(
            "You don't have permission to give clubhall coins.",
            ephemeral=True,
        )
        return
    register_user(str(user.id), user.display_name)
    added = safe_add_coins(str(user.id), amount)
    if added == 0:
        await interaction.response.send_message(
            "Clubhall coin limit reached. No coins added.", ephemeral=True
        )
    elif added < amount:
        await interaction.response.send_message(
            f"Partial success: Only {added} coins added due to server limit.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"{added} clubhall coins added to {user.display_name}.",
        )
