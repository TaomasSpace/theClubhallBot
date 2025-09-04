import discord
from db.DBHelper import register_user
from utils import has_command_permission

async def setstatpoints(
    interaction: discord.Interaction, user: discord.Member, amount: int
) -> None:
    if not has_command_permission(interaction.user, "setstatpoints", "admin"):
        await interaction.response.send_message(
            "Only the Owner can use this command.", ephemeral=True
        )
        return
    if amount < 0:
        await interaction.response.send_message(
            "Amount must be ≥ 0.", ephemeral=True
        )
        return
    uid = str(user.id)
    register_user(uid, user.display_name)
    _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
    _execute("UPDATE users SET stat_points = ? WHERE user_id = ?", (amount, uid))
    await interaction.response.send_message(
        f"✅ Set {user.display_name}'s stat points to {amount}.", ephemeral=True
    )

async def setstat(
    interaction: discord.Interaction, user: discord.Member, stat: str, amount: int
) -> None:
    if not has_command_permission(interaction.user, "setstat", "admin"):
        await interaction.response.send_message(
            "Only the Owner can use this command.", ephemeral=True
        )
        return
    from config import STAT_NAMES
    stat = stat.lower()
    if stat not in STAT_NAMES:
        await interaction.response.send_message(
            "Invalid stat name.", ephemeral=True
        )
        return
    if amount < 0:
        await interaction.response.send_message(
            "Amount must be ≥ 0.", ephemeral=True
        )
        return
    uid = str(user.id)
    register_user(uid, user.display_name)
    _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
    _execute(f"UPDATE users SET {stat} = ? WHERE user_id = ?", (amount, uid))
    await interaction.response.send_message(
        f"✅ Set {user.display_name}'s **{stat}** to **{amount}**.",
        ephemeral=True,
    )
