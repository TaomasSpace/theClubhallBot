import discord
from db.DBHelper import register_user, get_stats
from config import STAT_NAMES

async def stats(
    interaction: discord.Interaction, user: discord.Member | None = None
) -> None:
    target = user or interaction.user
    register_user(str(target.id), target.display_name)
    stats_data = get_stats(str(target.id))
    description = "\n".join(
        f"**{s.title()}**: {stats_data[s]}" for s in STAT_NAMES
    )
    embed = discord.Embed(
        title=f"{target.display_name}'s Stats",
        description=description,
        colour=discord.Colour.green(),
    )
    embed.set_footer(text=f"Unspent points: {stats_data['stat_points']}")
    await interaction.response.send_message(
        embed=embed, ephemeral=(user is None)
    )
