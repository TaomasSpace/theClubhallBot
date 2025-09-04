import asyncio
from datetime import datetime, timezone, timedelta
import discord
from db.DBHelper import create_giveaway
from utils import has_command_permission
from events import end_giveaway, active_giveaway_tasks

async def giveaway(
    interaction: discord.Interaction, duration: int, prize: str, winners: int
) -> None:
    if not has_command_permission(interaction.user, "giveaway", "admin"):
        await interaction.response.send_message(
            "Only admins and owners can use this command", ephemeral=True
        )
        return
    if winners < 1:
        await interaction.response.send_message(
            "You need at least 1 winner.", ephemeral=True
        )
        return
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"React with 🎉 to win **{prize}**!\n🔔 Duration: **{duration} min**.\n🏆 Winners: **{winners}**"
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(
        text=f"Created by: {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url,
    )
    await interaction.response.send_message(embed=embed)
    giveaway_msg = await interaction.original_response()
    await giveaway_msg.add_reaction("🎉")
    end_time = datetime.now(timezone.utc) + timedelta(minutes=duration)
    create_giveaway(
        str(giveaway_msg.id), str(giveaway_msg.channel.id), end_time, prize, winners
    )

    async def end_later():
        try:
            await asyncio.sleep(duration * 60)
            await end_giveaway(
                interaction.client, giveaway_msg.channel.id, giveaway_msg.id, prize, winners
            )
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(end_later())
    active_giveaway_tasks[giveaway_msg.id] = task
