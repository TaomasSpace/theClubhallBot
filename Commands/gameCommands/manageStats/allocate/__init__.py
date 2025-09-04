import discord
from config import STAT_NAMES, ROLE_THRESHOLDS
from db.DBHelper import (
    register_user,
    get_stats,
    increase_stat,
)

async def sync_stat_roles(member: discord.Member) -> None:
    stats = get_stats(str(member.id))
    for stat, (role_name, threshold) in ROLE_THRESHOLDS.items():
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role is None:
            continue
        has_r = role in member.roles
        meets = stats[stat] >= threshold
        if meets and not has_r:
            await member.add_roles(role, reason=f"{stat} {stats[stat]} = {threshold}")
        elif not meets and has_r:
            await member.remove_roles(
                role, reason=f"{stat} {stats[stat]} < {threshold}"
            )

async def allocate(
    interaction: discord.Interaction, stat: str, points: int
) -> None:
    stat = stat.lower()
    if stat not in STAT_NAMES:
        await interaction.response.send_message(
            "Invalid stat name.", ephemeral=True
        )
        return
    if points < 1:
        await interaction.response.send_message(
            "Points must be > 0.", ephemeral=True
        )
        return
    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)
    user_stats = get_stats(uid)
    if user_stats["stat_points"] < points:
        await interaction.response.send_message(
            "Not enough unspent points.", ephemeral=True
        )
        return
    increase_stat(uid, stat, points)
    await sync_stat_roles(interaction.user)
    await interaction.response.send_message(
        f"{stat.title()} increased by {points}."
    )
