import discord
from db.DBHelper import get_money, set_money
from utils import has_command_permission

async def remove(
    interaction: discord.Interaction, user: discord.Member, amount: int
) -> None:
    if not has_command_permission(interaction.user, "remove", "admin"):
        await interaction.response.send_message(
            "You don't have permission to remove clubhall coins.",
            ephemeral=True,
        )
        return
    current = get_money(str(user.id))
    set_money(str(user.id), max(0, current - amount))
    await interaction.response.send_message(
        f"{amount} clubhall coins removed from {user.display_name}."
    )
